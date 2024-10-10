from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, Filters, CallbackContext
from dotenv import load_dotenv
import logging, re, paramiko, os, subprocess
import psycopg2

logging.basicConfig(filename='app.log', format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
log = logging.getLogger(__name__)

load_dotenv()

REMOTE_HOST = os.getenv('RM_HOST')
SSH_PORT = os.getenv('RM_PORT')
SSH_USER = os.getenv('RM_USER')
SSH_PASS = os.getenv('RM_PASSWORD')

PG_DB = os.getenv('DB_DATABASE')
PG_USER = os.getenv('DB_USER')
PG_PASS = os.getenv('DB_PASSWORD')
PG_HOST = os.getenv('DB_HOST')
PG_PORT = os.getenv('DB_PORT')

BOT_TOKEN = os.getenv('TOKEN')
PG_LOG_PATH = "/var/log/postgresql/postgresql.log"


STATE_PHONE, STATE_EMAIL, PHONE_CONFIRM, EMAIL_CONFIRM, PASSWORD_CHECK = range(5)

def init_bot(update, context):
    update.message.reply_text(f"Добро пожаловать, {update.effective_user.full_name}! Введите /help для списка команд.")


def phone_search(update, context):
    update.message.reply_text("Введите текст для поиска номеров.")
    return STATE_PHONE

def process_phone_input(update, context):
    PHONE_PATTERN = r"\+?7[ -]?\(?\d{3}\)?[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}|\+?7[ -]?\d{10}|\+?7[ -]?\d{3}[ -]?\d{3}[ -]?\d{4}|8[ -]?\(?\d{3}\)?[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}|8[ -]?\d{10}|8[ -]?\d{3}[ -]?\d{3}[ -]?\d{4}"
    text = update.message.text
    phone_matches = re.findall(PHONE_PATTERN, text)
    if not phone_matches:
        update.message.reply_text("Номеров не найдено.")
        return ConversationHandler.END
    context.user_data['phones'] = phone_matches
    buttons = [[InlineKeyboardButton("Сохранить", callback_data="yes")],
               [InlineKeyboardButton("Не сохранять", callback_data="no")]]
    update.message.reply_text(f"Найденные номера: {' '.join(phone_matches)}. Сохранить?", reply_markup=InlineKeyboardMarkup(buttons))
    return PHONE_CONFIRM

def confirm_phone_save(update, context):
    query = update.callback_query
    query.answer()
    if query.data == "yes":
        store_phones(context.user_data['phones'])
        query.edit_message_text(text="Номера сохранены.")
    else:
        query.edit_message_text(text="Сохранение отменено.")
    return ConversationHandler.END

def store_phones(phone_list):
    conn = psycopg2.connect(dbname=PG_DB, user=PG_USER, password=PG_PASS, host=PG_HOST, port=PG_PORT)
    cursor = conn.cursor()
    for number in phone_list:
        cursor.execute("INSERT INTO phone_numbers (phone_number) VALUES (%s) ON CONFLICT DO NOTHING", (number,))
    conn.commit()
    cursor.close()
    conn.close()


def email_search(update, context):
    EMAIL_PATTERN = r'\b[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b'
    update.message.reply_text("Введите текст для поиска email.")
    return STATE_EMAIL

def process_email_input(update, context):
    text = update.message.text
    email_matches = re.findall(EMAIL_PATTERN, text)
    if not email_matches:
        update.message.reply_text("Email не найден.")
        return ConversationHandler.END
    context.user_data['emails'] = email_matches
    buttons = [[InlineKeyboardButton("Сохранить", callback_data="yes")],
               [InlineKeyboardButton("Не сохранять", callback_data="no")]]
    update.message.reply_text(f"Найдены email: {' '.join(email_matches)}. Сохранить?", reply_markup=InlineKeyboardMarkup(buttons))
    return EMAIL_CONFIRM

def confirm_email_save(update, context):
    query = update.callback_query
    query.answer()
    if query.data == "yes":
        store_emails(context.user_data['emails'])
        query.edit_message_text(text="Emails сохранены.")
    else:
        query.edit_message_text(text="Сохранение отменено.")
    return ConversationHandler.END

def store_emails(email_list):
    conn = psycopg2.connect(dbname=PG_DB, user=PG_USER, password=PG_PASS, host=PG_HOST, port=PG_PORT)
    cursor = conn.cursor()
    for email in email_list:
        cursor.execute("INSERT INTO emails (email) VALUES (%s) ON CONFLICT DO NOTHING", (email,))
    conn.commit()
    cursor.close()
    conn.close()

def password_check(update, context):
    update.message.reply_text("Введите пароль для проверки.")
    return PASSWORD_CHECK

def check_password(update, context):
    pwd = update.message.text
    if re.search(r'[=+\-_\/\\|]', pwd):
        update.message.reply_text("Некорректные символы в пароле.")
    elif re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()]).{8,}$', pwd):
        update.message.reply_text("Пароль сложный.")
    else:
        update.message.reply_text("Пароль простой.")
    return ConversationHandler.END

def ssh_command(command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(REMOTE_HOST, port=SSH_PORT, username=SSH_USER, password=SSH_PASS)
    stdin, stdout, stderr = ssh.exec_command(command)
    result = stdout.read().decode('utf-8') + stderr.read().decode('utf-8')
    ssh.close()
    return result

def release_info(update, context):
    result = ssh_command("lsb_release -a")
    update.message.reply_text(result)

def memory_info(update, context):
    result = ssh_command("free -h")
    update.message.reply_text(result)

def process_list(update, context):
    result = ssh_command("ps aux | head -n 5")
    update.message.reply_text(result)

def cancel(update, context):
    update.message.reply_text("Операция прервана.")
    return ConversationHandler.END

def run_bot():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    phone_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('phone_search', phone_search)],
        states={
            STATE_PHONE: [MessageHandler(Filters.text, process_phone_input)],
            PHONE_CONFIRM: [CallbackQueryHandler(confirm_phone_save)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    email_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('email_search', email_search)],
        states={
            STATE_EMAIL: [MessageHandler(Filters.text, process_email_input)],
            EMAIL_CONFIRM: [CallbackQueryHandler(confirm_email_save)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    password_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('password_check', password_check)],
        states={PASSWORD_CHECK: [MessageHandler(Filters.text, check_password)]},
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(phone_conv_handler)
    dp.add_handler(email_conv_handler)
    dp.add_handler(password_conv_handler)
    dp.add_handler(CommandHandler('start', init_bot))
    dp.add_handler(CommandHandler('release_info', release_info))
    dp.add_handler(CommandHandler('memory_info', memory_info))
    dp.add_handler(CommandHandler('process_list', process_list))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    run_bot()
