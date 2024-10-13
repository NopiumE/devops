import logging
import re
import paramiko
import os
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, CallbackQueryHandler, ConversationHandler, 
                          MessageHandler, Filters, CallbackContext)
from dotenv import load_dotenv
import psycopg2
from psycopg2 import Error

load_dotenv()

logging.basicConfig(filename='bot.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TOKEN')
DB_DATABASE = os.getenv('DB_DATABASE')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
RM_HOST = os.getenv('RM_HOST')
RM_PORT = os.getenv('RM_PORT')
RM_USER = os.getenv('RM_USER')
RM_PASSWORD = os.getenv('RM_PASSWORD')
LOG_FILE_PATH = "/var/log/postgresql/postgresql.log"

CHOOSING, GET_PACKAGE_INFO, INPUT_TEXT_PHONE, CONFIRM_SAVE_PHONE, INPUT_TEXT_EMAIL, CONFIRM_SAVE_EMAIL, VERIFY_PASSWORD = range(7)

def get_email_addresses(update, context):
    get_data_from_db(update, "SELECT * FROM emails", "Адреса электронной почты:")

def find_phone_numbers(update, context):
    update.message.reply_text("Пожалуйста, отправьте текст для поиска номеров телефона.")
    return INPUT_TEXT_PHONE

def get_release(update, context):
    execute_ssh_command(update, 'cat /etc/os-release', "Информация о релизе:")

def find_email_address(update, context):
    update.message.reply_text("Пожалуйста, отправьте текст для поиска адреса электронной почты.")
    return INPUT_TEXT_EMAIL

def get_df(update, context):
    execute_ssh_command(update, 'df -h', "Состояние файловой системы:")

def start(update, context):
    update.message.reply_text(f'Привет {update.effective_user.full_name}! Используйте команду /help для получения информации о боте.')

def verify_password_command(update, context):
    update.message.reply_text('Введите пароль для проверки:')
    return VERIFY_PASSWORD

def input_text_pn(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    phone_numbers = re.findall(PHONE_REGEX, text)
    
    if not phone_numbers:
        update.message.reply_text("В введенном тексте номера телефона не найдены.")
        return ConversationHandler.END

    context.user_data['phone_numbers'] = phone_numbers
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Да", callback_data="yes")],
        [InlineKeyboardButton("Нет", callback_data="no")]
    ])
    update.message.reply_text(f"Найдены номера: {' '.join(phone_numbers)}. Хотите сохранить их в базу данных?",
                              reply_markup=reply_markup)
    return CONFIRM_SAVE_PHONE

def save_email_address(email_addresses):
    with psycopg2.connect(dbname=DB_DATABASE, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT) as conn:
        with conn.cursor() as cur:
            for email in email_addresses:
                cur.execute("INSERT INTO emails (email) VALUES (%s) ON CONFLICT DO NOTHING", (email,))
            conn.commit()

def save_phone_numbers(phone_numbers):
    with psycopg2.connect(dbname=DB_DATABASE, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT) as conn:
        with conn.cursor() as cur:
            for number in phone_numbers:
                cur.execute("INSERT INTO phone_numbers (phone_number) VALUES (%s) ON CONFLICT DO NOTHING", (number,))
            conn.commit()

def get_free(update, context):
    execute_ssh_command(update, 'free -h', "Состояние оперативной памяти:")

def get_auths(update, context):
    execute_ssh_command(update, f'tail -n 10 {LOG_FILE_PATH}', "Последние 10 входов в систему:")

def confirm_save_email(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    if query.data == "yes":
        save_email_address(context.user_data['email_addresses'])
        query.edit_message_text(text="Адреса электронной почты сохранены успешно.")
    else:
        query.edit_message_text(text="Сохранение отменено.")
    
    return ConversationHandler.END

def execute_ssh_command(update, command, message_prefix):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(RM_HOST, port=RM_PORT, username=RM_USER, password=RM_PASSWORD)
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode('utf-8') + stderr.read().decode('utf-8')
        update.message.reply_text(f"{message_prefix}\n{output.strip()}")
    except Exception as e:
        update.message.reply_text(f"Ошибка: {e}")
    finally:
        ssh.close()

def cancel(update, context):
    update.message.reply_text('Операция отменена.')
    return ConversationHandler.END

def input_text_em(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    email_addresses = re.findall(EMAIL_REGEX, text)
    
    if not email_addresses:
        update.message.reply_text("В введенном тексте адреса электронной почты не найдены.")
        return ConversationHandler.END

    context.user_data['email_addresses'] = email_addresses
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Да", callback_data="yes")],
        [InlineKeyboardButton("Нет", callback_data="no")]
    ])
    update.message.reply_text(f"Найдены адреса: {' '.join(email_addresses)}. Хотите сохранить их в базу данных?",
                              reply_markup=reply_markup)
    return CONFIRM_SAVE_EMAIL

def get_ps(update, context):
    execute_ssh_command(update, 'ps aux', "Запущенные процессы:")

def get_uptime(update, context):
    execute_ssh_command(update, 'uptime', "Время работы системы:")

def get_mpstat(update, context):
    execute_ssh_command(update, 'mpstat', "Производительность системы:")

def confirm_save_phone(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    if query.data == "yes":
        save_phone_numbers(context.user_data['phone_numbers'])
        query.edit_message_text(text="Номера телефона сохранены успешно.")
    else:
        query.edit_message_text(text="Сохранение отменено.")
    
    return ConversationHandler.END

def get_repl_logs(update: Update, context: CallbackContext) -> None:
    try:
        result = subprocess.run(
            ["bash", "-c", f"cat {LOG_FILE_PATH} | grep repl | tail -n 15"],
            capture_output=True,
            text=True
        )
        logs = result.stdout
        if logs:
            update.message.reply_text(f"Последние репликационные логи:\n{logs}")
        else:
            update.message.reply_text("Репликационные логи не найдены.")
    except Exception as e:
        update.message.reply_text(f"Ошибка при получении логов: {str(e)}")


def get_ss(update, context):
    execute_ssh_command(update, 'ss -tuln', "Используемые порты:")

def get_services(update, context):
    execute_ssh_command(update, 'systemctl list-units --type=service', "Запущенные сервисы:")

def get_critical(update, context):
    execute_ssh_command(update, f'tail -n 5 {LOG_FILE_PATH}', "Последние 5 критических событий:")

def get_apt_list(update, context):
    execute_ssh_command(update, 'dpkg -l', "Установленные пакеты:")

def verify_password(update, context):
    password_input = update.message.text
    
    if re.search(r'[=+\-_\/\\|]', password_input):
        update.message.reply_text('Пароль содержит некорректные символы.')
    elif re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()]).{8,}$', password_input):
        update.message.reply_text('Пароль сложный')
    else:
        update.message.reply_text('Пароль простой')

    return ConversationHandler.END

def get_data_from_db(update, query, message_prefix):
    try:
        with psycopg2.connect(dbname=DB_DATABASE, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                if not rows:
                    update.message.reply_text("Нет данных.")
                    return

                result = "\n".join([f"{row[0]}" for row in rows])
                update.message.reply_text(f"{message_prefix}\n{result}")
    except Exception as e:
        update.message.reply_text(f"Ошибка: {e}")

def main():
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher
    
    phone_handler = ConversationHandler(
        entry_points=[CommandHandler('find_phone_numbers', find_phone_numbers)],
        states={
            INPUT_TEXT_PHONE: [MessageHandler(Filters.text & ~Filters.command, input_text_pn)],
            CONFIRM_SAVE_PHONE: [CallbackQueryHandler(confirm_save_phone)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    email_handler = ConversationHandler(
        entry_points=[CommandHandler('find_email_address', find_email_address)],
        states={
            INPUT_TEXT_EMAIL: [MessageHandler(Filters.text & ~Filters.command, input_text_em)],
            CONFIRM_SAVE_EMAIL: [CallbackQueryHandler(confirm_save_email)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    password_handler = ConversationHandler(
        entry_points=[CommandHandler('verify_password', verify_password_command)],
        states={
            VERIFY_PASSWORD: [MessageHandler(Filters.text & ~Filters.command, verify_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(phone_handler)
    dispatcher.add_handler(email_handler)
    dispatcher.add_handler(password_handler)
    dispatcher.add_handler(CommandHandler("get_release", get_release))
    dispatcher.add_handler(CommandHandler("get_uptime", get_uptime))
    dispatcher.add_handler(CommandHandler("get_df", get_df))
    dispatcher.add_handler(CommandHandler("get_free", get_free))
    dispatcher.add_handler(CommandHandler("get_mpstat", get_mpstat))
    dispatcher.add_handler(CommandHandler("get_ps", get_ps))
    dispatcher.add_handler(CommandHandler("get_ss", get_ss))
    dispatcher.add_handler(CommandHandler("get_services", get_services))
    dispatcher.add_handler(CommandHandler("get_apt_list", get_apt_list))
    dispatcher.add_handler(CommandHandler("get_auths", get_auths))
    dispatcher.add_handler(CommandHandler("get_critical", get_critical))
    dispatcher.add_handler(CommandHandler("get_repl_logs", get_repl_logs))
    dispatcher.add_handler(CommandHandler("get_emails", get_email_addresses))
    dispatcher.add_handler(CommandHandler("get_phone_numbers", find_phone_numbers))
    dispatcher.add_handler(CommandHandler("cancel", cancel))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
