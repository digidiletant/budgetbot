import logging
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Траты").sheet1

# Константы для этапов разговора
ENTER_AMOUNT, CHOOSE_DATE_OPTION, ENTER_DATE, CHOOSE_PAYER, CHOOSE_PAYMENT_OPTION, CHOOSE_PAYMENT_METHOD, ENTER_PLACE, CHOOSE_CATEGORY = range(8)

# Стартовый обработчик
def start(update: Update, _: CallbackContext) -> int:
    update.message.reply_text("Введите сумму трат:")
    return ENTER_AMOUNT

# Обработчик суммы
def enter_amount(update: Update, context: CallbackContext) -> int:
    amount = update.message.text.replace(',', '.')
    try:
        context.user_data['amount'] = float(amount)
        reply_keyboard = [['Указать дату', 'Ввести сумму']]
        update.message.reply_text(
            "Выберите опцию:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return CHOOSE_DATE_OPTION
    except ValueError:
        update.message.reply_text("Пожалуйста, введите корректное число.")
        return ENTER_AMOUNT

# Обработчик выбора опции даты
def choose_date_option(update: Update, context: CallbackContext) -> int:
    if update.message.text == 'Указать дату':
        update.message.reply_text("Введите дату в формате ддммгг:")
        return ENTER_DATE
    else:
        context.user_data['date'] = datetime.datetime.now().strftime("%d%m%y")
        reply_keyboard = [['Ринат', 'Коля', 'Nicolas']]
        update.message.reply_text(
            "Выберите плательщика:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return CHOOSE_PAYER

# Обработчик ввода даты
def enter_date(update: Update, context: CallbackContext) -> int:
    context.user_data['date'] = update.message.text
    reply_keyboard = [['Ринат', 'Коля', 'Nicolas']]
    update.message.reply_text(
        "Выберите плательщика:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return CHOOSE_PAYER

# Обработчик выбора плательщика
def choose_payer(update: Update, context: CallbackContext) -> int:
    context.user_data['payer'] = update.message.text
    reply_keyboard = [['Выбрать способ оплаты', 'Указать место покупки']]
    update.message.reply_text(
        "Выберите опцию:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return CHOOSE_PAYMENT_OPTION

# Обработчик выбора опции оплаты
def choose_payment_option(update: Update, context: CallbackContext) -> int:
    if update.message.text == 'Указать место покупки':
        context.user_data['payment_method'] = 'Freedom'
        update.message.reply_text("Введите место покупки:")
        return ENTER_PLACE
    else:
        reply_keyboard = [['Revolut', 'BNP', 'Cash', 'Freedom']]
        update.message.reply_text(
            "Выберите способ оплаты:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return CHOOSE_PAYMENT_METHOD

# Обработчик выбора способа оплаты
def choose_payment_method(update: Update, context: CallbackContext) -> int:
    context.user_data['payment_method'] = update.message.text
    update.message.reply_text("Введите место покупки:")
    return ENTER_PLACE

# Обработчик ввода места покупки
def enter_place(update: Update, context: CallbackContext) -> int:
    context.user_data['place'] = update.message.text
    reply_keyboard = [['Транспорт', 'Продукты', 'Кафе', 'Товары', 'Жильё', 'Документы', 'Связь', 'Досуг', 'Комиссия', 'Путешествия', 'Подарки', 'Спорт']]
    update.message.reply_text(
        "Выберите категорию трат:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return CHOOSE_CATEGORY

# Обработчик выбора категории
def choose_category(update: Update, context: CallbackContext) -> int:
    context.user_data['category'] = update.message.text
    # Добавляем запись в Google Sheets
    sheet.append_row([
        context.user_data['date'],
        context.user_data['amount'],
        context.user_data['payer'],
        context.user_data['payment_method'],
        context.user_data['place'],
        context.user_data['category']
    ])
    update.message.reply_text("Трата успешно добавлена!")
    return ConversationHandler.END

# Обработчик команды /cancel
def cancel(update: Update, _: CallbackContext) -> int:
    update.message.reply_text("Отмена операции.")
    return ConversationHandler.END

def main() -> None:
    # Получаем токен бота из переменных окружения
    token = os.getenv("YOUR_TELEGRAM_BOT_TOKEN")

    # Создаем Updater и передаем ему токен вашего бота.
    updater = Updater(token)

    # Получаем диспетчера для регистрации обработчиков
    dispatcher = updater.dispatcher

    # Настройка ConversationHandler с состояниями
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ENTER_AMOUNT: [MessageHandler(Filters.text & ~Filters.command, enter_amount)],
            CHOOSE_DATE_OPTION: [MessageHandler(Filters.text & ~Filters.command, choose_date_option)],
            ENTER_DATE: [MessageHandler(Filters.text & ~Filters.command, enter_date)],
            CHOOSE_PAYER: [MessageHandler(Filters.text & ~Filters.command, choose_payer)],
            CHOOSE_PAYMENT_OPTION: [MessageHandler(Filters.text & ~Filters.command, choose_payment_option)],
            CHOOSE_PAYMENT_METHOD: [MessageHandler(Filters.text & ~Filters.command, choose_payment_method)],
            ENTER_PLACE: [MessageHandler(Filters.text & ~Filters.command, enter_place)],
            CHOOSE_CATEGORY: [MessageHandler(Filters.text & ~Filters.command, choose_category)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)

    # Запуск бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

