import logging
import os
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import datetime

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка Google Sheets из переменной окружения
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Чтение JSON-данных из переменной окружения
credentials_json = os.getenv('GOOGLE_CREDENTIALS_JSON')

if credentials_json is None:
    raise ValueError("GOOGLE_CREDENTIALS_JSON environment variable not set")

# Преобразование JSON-данных в словарь
credentials_info = json.loads(credentials_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_info, scope)
client = gspread.authorize(creds)

# Открытие таблицы Google Sheets
spreadsheet_id = "1MTFF7XKkoTIOlXlYUb9dDo9zwupYpM7Efx00AFHk86Y"  # Замените на ваш ID таблицы
sheet = client.open_by_key(spreadsheet_id).worksheet("Траты")

# Константы для этапов разговора
ENTER_AMOUNT, CHOOSE_DATE_OPTION, ENTER_DATE, CHOOSE_PAYER, CHOOSE_PAYMENT_OPTION, CHOOSE_PAYMENT_METHOD, ENTER_PLACE, CHOOSE_CATEGORY = range(8)

# Вспомогательная функция для разбивки списка на подсписки фиксированного размера
def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

# Стартовый обработчик
async def start(update: Update, context: CallbackContext) -> int:
    context.user_data.clear()  # Очистка предыдущих данных
    await update.message.reply_text("Сколько потратил?")
    return ENTER_AMOUNT

# Обработчик суммы
async def enter_amount(update: Update, context: CallbackContext) -> int:
    amount = update.message.text.replace(',', '.')
    try:
        context.user_data['amount'] = float(amount)
        reply_keyboard = [['Указать дату (если не сегодня)', 'И кто башляет?']]
        await update.message.reply_text(
            "Выбери опцию:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return CHOOSE_DATE_OPTION
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи корректное число.")
        return ENTER_AMOUNT

# Обработчик выбора опции даты
async def choose_date_option(update: Update, context: CallbackContext) -> int:
    user_input = update.message.text
    logger.info(f"Received input for date option: {user_input}")

    if user_input == 'Указать дату (если не сегодня)':
        await update.message.reply_text("Введи дату в формате ДДММ:")
        return ENTER_DATE
    elif user_input == 'И кто башляет?':
        if 'date' not in context.user_data:
            context.user_data['date'] = datetime.datetime.now().strftime("%d.%m.%Y")
        reply_keyboard = [['Ринат', 'Коля', 'Nicolas']]
        await update.message.reply_text(
            "И кто башляет?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return CHOOSE_PAYER
    else:
        return CHOOSE_DATE_OPTION

# Обработчик ввода даты
async def enter_date(update: Update, context: CallbackContext) -> int:
    input_date = update.message.text
    logger.info(f"Received input date: {input_date}")

    try:
        if len(input_date) != 4 or not input_date.isdigit():
            raise ValueError("Некорректный формат даты. Ожидается ДДММ.")
        
        current_year = datetime.datetime.now().year
        parsed_date = datetime.datetime.strptime(input_date, "%d%m")
        formatted_date = f"{parsed_date.day:02d}.{parsed_date.month:02d}.{current_year}"
        context.user_data['date'] = formatted_date

        logger.info(f"Parsed and formatted date: {formatted_date}")

        reply_keyboard = [['Ринат', 'Коля', 'Nicolas']]
        await update.message.reply_text(
            "И кто башляет?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return CHOOSE_PAYER
    except ValueError as e:
        await update.message.reply_text(f"Ошибка: {e}. Пожалуйста, введи дату в формате ДДММ.")
        return ENTER_DATE

# Обработчик выбора плательщика
async def choose_payer(update: Update, context: CallbackContext) -> int:
    payer = update.message.text
    if payer in ['Ринат', 'Коля', 'Nicolas']:
        context.user_data['payer'] = payer
        reply_keyboard = [['Выбрать способ оплаты (если не Freedom)', 'Где потратил?']]
        await update.message.reply_text(
            "Выбери опцию:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return CHOOSE_PAYMENT_OPTION
    else:
        return CHOOSE_PAYER

# Обработчик выбора опции оплаты
async def choose_payment_option(update: Update, context: CallbackContext) -> int:
    user_input = update.message.text
    logger.info(f"Received input for payment option: {user_input}")
    
    if user_input == 'Где потратил?':
        context.user_data['payment_method'] = 'Freedom'
        await update.message.reply_text("Где потратил?")
        return ENTER_PLACE
    elif user_input == 'Выбрать способ оплаты (если не Freedom)':
        reply_keyboard = [['Revolut', 'BNP', 'Cash', 'Freedom']]
        await update.message.reply_text(
            "Выбери способ оплаты",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return CHOOSE_PAYMENT_METHOD
    else:
        return CHOOSE_PAYMENT_OPTION

# Обработчик выбора способа оплаты
async def choose_payment_method(update: Update, context: CallbackContext) -> int:
    context.user_data['payment_method'] = update.message.text
    await update.message.reply_text("Где потратил?")
    return ENTER_PLACE

# Обработчик ввода места покупки
async def enter_place(update: Update, context: CallbackContext) -> int:
    context.user_data['place'] = update.message.text
    categories = ['Транспорт', 'Продукты', 'Кафе', 'Товары', 'Жильё', 'Документы', 'Связь', 'Досуг', 'Комиссия', 'Путешествия', 'Подарки', 'Спорт']
    
    # Разбиваем список категорий на строки по три кнопки
    reply_keyboard = list(chunks(categories, 3))
    
    await update.message.reply_text(
        "Выбери категорию:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return CHOOSE_CATEGORY

# Обработчик выбора категории
async def choose_category(update: Update, context: CallbackContext) -> int:
    date = context.user_data.get('date', datetime.datetime.now().strftime("%d.%m.%Y"))
    context.user_data['category'] = update.message.text
    sheet.append_row([
        date,
        context.user_data['amount'],
        context.user_data['payer'],
        context.user_data['payment_method'],
        context.user_data['place'],
        context.user_data['category']
    ])
    await update.message.reply_text("Трата успешно добавлена!")

    # Завершение текущей операции и возврат к началу
    context.user_data.clear()  # Очистка состояния после завершения операции
    await update.message.reply_text("Можешь начать новую операцию, отправив сумму.")
    return ENTER_AMOUNT

# Обработчик команды /cancel
async def cancel(update: Update, _: CallbackContext) -> int:
    await update.message.reply_text("Операция отменена.")
    context.user_data.clear()  # Очистка состояния при отмене
    return ConversationHandler.END

# Обработчик всех сообщений, включая числа
async def handle_message(update: Update, context: CallbackContext) -> int:
    if update.message.text.isdigit():
        if 'amount' not in context.user_data:
            context.user_data['amount'] = float(update.message.text)
            reply_keyboard = [['Указать дату (если не сегодня)', 'И кто башляет?']]
            await update.message.reply_text(
                "Выбери опцию:",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
            )
            return CHOOSE_DATE_OPTION
        else:
            await update.message.reply_text("Сначала завершите текущую операцию.")
            return ConversationHandler.END

    # Игнорируем сообщения, не относящиеся к текущему шагу
    return ConversationHandler.END

def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")  # Используем переменную окружения для токена

    if not token:
        raise ValueError("No TELEGRAM_BOT_TOKEN environment variable set")

    application = Application.builder().token(token).build()

    # Настройка ConversationHandler с состояниями
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount)],
            CHOOSE_DATE_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_date_option)],
            ENTER_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_date)],
            CHOOSE_PAYER: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_payer)],
            CHOOSE_PAYMENT_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_payment_option)],
            CHOOSE_PAYMENT_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_payment_method)],
            ENTER_PLACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_place)],
            CHOOSE_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_category)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == '__main__':
    main()
