import anuncieaqui
import configparser
import datetime
import epub_meta
import json
import logging
import logging.handlers
import os
import pika
import redis
import sqlite3
import subprocess
import time
import urllib.request

import i18n
import telebot
import weasyprint
from telebot import types
from validate_email import validate_email

i18n.load_path.append("i18n")
i18n.set("fallback", "en-us")

config = configparser.ConfigParser()
config.sections()
BOT_CONFIG_FILE = "kindle.conf"
config.read(BOT_CONFIG_FILE)
log_file = config["DEFAULT"]["logfile"]
TOKEN = config["DEFAULT"]["TOKEN"]
BLOCKED = config["DEFAULT"]["BLOCKED"]
db = config["SQLITE3"]["data_base"]
table = config["SQLITE3"]["table"]

bot = telebot.TeleBot(TOKEN)

rabbitmq_con = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
rabbit = rabbitmq_con.channel()
rabbit.queue_declare(queue='Send2KindleBotFast', durable=True)
rabbit.queue_declare(queue='Send2KindleBotSlow', durable=True)

class Document:
    def __init__(self, name):
        self.name = name[:20] + name[-5:]

def check_interval(data, user_lang):
    user_id = data[1]
    file_url = data[7]
    last_usage = data[5]
    try:
        interval = (
            datetime.datetime.now()
            - datetime.datetime.strptime(last_usage, "%Y-%m-%d %H:%M:%S.%f")
        ).total_seconds()
    except ValueError:
        interval = 901
    if interval < 8:
        return False
    elif interval < 30:
        try:
            send_message(user_id, i18n.t("bot.slowmodesec", locale=user_lang))
        except:
            send_message(user_id, "Wait 30 seconds")
        return False
    elif (
        ".mobi" in file_url
        or ".cbr" in file_url
        or ".cbz" in file_url
        or ".azw3" in file_url
    ):
        if interval < 900:
            try:
                send_message(
                    user_id, i18n.t("bot.slowmode", locale=user_lang)
                )
            except:
                send_message(user_id, "Wait 15 minutes")
            return False
    return True

def send_mail(data, subject, lang):
    if not check_interval(data, lang):
        return 0
    msg_sent = send_message(
        data[1], str(u"\U0001F5DE") + i18n.t("bot.sendingfile",
        locale=lang), parse_mode="HTML",
    )
    rabbitmq_con = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    rabbit = rabbitmq_con.channel()
    if (
        ".mobi" in data[7]
        or ".cbr" in data[7]
        or ".cbz" in data[7]
        or ".azw3" in data[7]
    ):
        queue = 'Send2KindleBotSlow'
    else:
        queue = 'Send2KindleBotFast'
    msg = (f'{{"from":"{data[2]}", "to":"{data[3]}", "subject":"{subject}", ' 
        f'"user_id":"{data[1]}", "file_url":"{data[7]}", "lang":"{lang}", '
        f'"message_id":"{msg_sent.message_id}"}}')
    rabbit.basic_publish(
        exchange='',
        routing_key=queue,
        body=msg,
        properties=pika.BasicProperties(
            delivery_mode = pika.spec.PERSISTENT_DELIVERY_MODE
        )
    )
    rabbitmq_con.close()
    upd_user_last(db, table, data[1])

def send_message(chatid, text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=None):
    msg = bot.send_message(chatid, text, parse_mode=parse_mode,
        disable_web_page_preview=disable_web_page_preview,
        reply_markup=reply_markup
    )
    return msg

def epubauthors(file_path):
    authors = epub_meta.get_epub_metadata(file_path).authors
    return authors

def convert_format(file_name_original, chatid):
    logger_info.info(
        str(datetime.datetime.now())
        + " CONVERT: "
        + str(chatid)
        + " "
        + file_name_original
    )
    bot.send_chat_action(chatid, "upload_document")
    file_name_converted = file_name_original.replace(
        file_name_original.split(".")[-1], ".epub"
    )

    if ".cbr" in file_name_original or ".cbz" in file_name_original:
        subprocess.Popen(
            [
                "ebook-convert",
                file_name_original,
                file_name_converted,
                "--output-profile",
                "tablet",
            ]
        ).wait()
    else:
        subprocess.Popen(
            ["ebook-convert", file_name_original, file_name_converted]
        ).wait()

    os.remove(file_name_original)

    return file_name_converted


# Get file from URL
def open_file(file_url, chatid):
    if "api.telegram.org/file" not in file_url:
        return file_url

    try:
        try:
            r = redis.Redis(host='localhost', port=6379, db=0)
            fname = r.get(chatid).decode('utf-8')
            r.delete(chatid)
            file_name, headers = urllib.request.urlretrieve(
                file_url, fname
            )
        except:
            file_name, headers = urllib.request.urlretrieve(
                file_url, file_url.split("/")[-1]
            )
    except KeyError:
        file_name, headers = urllib.request.urlretrieve(
            file_url, file_url.split("/")[-1]
        )

    new_file_name = (
        os.path.splitext(file_name)[0][:15] + "." + file_name.split(".")[-1]
    )
    os.rename(file_name, new_file_name)

    return new_file_name

# Add user to database
def add_user(db, table, chatid):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    aux = (
        """INSERT INTO {} (chatid, remetente, destinatario, criacao, usado)
        VALUES ('{}', '', '',
        '{}', '{}')"""
    ).format(
        table,
        chatid,
        str(datetime.datetime.now()),
        str(datetime.datetime.now()),
    )
    logger_info.info(str(datetime.datetime.now()) + "\tUSER:\t" + str(chatid))
    cursor.execute(aux)
    conn.commit()
    conn.close()


# Update user last usage
def upd_user_last(db, table, chatid):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    aux = (
        """UPDATE {} SET usado = {}
        WHERE chatid = {}"""
    ).format(table, '"' + str(datetime.datetime.now()) + '"', chatid)
    cursor.execute(aux)
    conn.commit()
    conn.close()


def upd_user_file(db, table, chatid, file_url):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    aux = (
        """UPDATE {} SET arquivo = {}
        WHERE chatid = {}"""
    ).format(table, '"' + file_url + '"', chatid)
    cursor.execute(aux)
    conn.commit()
    conn.close()


# Update user e-mail
def upd_user_email(db, table, chatid, email):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    if "@kindle." in email.lower() or "@free.kindle." in email.lower():
        aux = (
            """UPDATE {} SET destinatario = {}
            WHERE chatid = {}"""
        ).format(table, email, chatid)
    else:
        aux = (
            """UPDATE {} SET remetente = {}
            WHERE chatid = {}"""
        ).format(table, email, chatid)
    logger_info.info(
        str(datetime.datetime.now()) + "\tUPD:\t" + str(chatid) + "\t" + email
    )
    cursor.execute(aux)
    conn.commit()
    conn.close()


# Select user on database
def select_user(db, table, chatid, field):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    aux = (
        '''SELECT {} FROM "{}" WHERE
        chatid="{}"'''
    ).format(field, table, chatid)
    cursor.execute(aux)
    usuarios = cursor.fetchone()
    if usuarios:
        data = usuarios
    else:
        add_user(db, table, chatid)
        data = ""
    conn.close()
    return data


def set_buttons(lang="en-us"):
    global button
    global button2
    button = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(
        i18n.t("bot.btn1", locale=lang), callback_data="/send"
    )
    btn2 = types.InlineKeyboardButton(
        i18n.t("bot.btn2", locale=lang), callback_data="/email"
    )
    button.row(btn1, btn2)
    button2 = types.InlineKeyboardMarkup()
    btn3 = types.InlineKeyboardButton(
        i18n.t("bot.btn3", locale=lang), callback_data="/as_is"
    )
    btn4 = types.InlineKeyboardButton(
        i18n.t("bot.btn4", locale=lang), callback_data="/converted"
    )
    button2.row(btn3, btn4)


if __name__ == "__main__":
    cmds = ["/start", "/send", "/info", "/help", "/email"]
    LOG_INFO_FILE = log_file
    logger_info = logging.getLogger("InfoLogger")
    logger_info.setLevel(logging.INFO)
    handler_info = logging.handlers.TimedRotatingFileHandler(
        LOG_INFO_FILE,
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    logger_info.addHandler(handler_info)

    @bot.message_handler(commands=["help"])
    def help(message):
        user_lang = (message.from_user.language_code or "en-us").lower()
        send_message(
            message.from_user.id,
            i18n.t("bot.help", locale=user_lang),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

    @bot.message_handler(commands=["tos"])
    def tos(message):
        user_lang = (message.from_user.language_code or "en-us").lower()
        send_message(
            message.from_user.id,
            i18n.t("bot.tos", locale=user_lang),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

    @bot.message_handler(commands=["info"])
    def info(message):
        user_lang = (message.from_user.language_code or "en-us").lower()
        send_message(
            message.from_user.id,
            i18n.t("bot.info", locale=user_lang),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

    @bot.message_handler(commands=["start"])
    def start(message):
        user_lang = (message.from_user.language_code or "en-us").lower()
        set_buttons(user_lang)
        data = select_user(db, table, message.from_user.id, "*")

        logger_info.info(
            str(datetime.datetime.now())
            + " START: "
            + str(message.from_user.id)
            + " "
            + str(message.message_id)
        )

        try:
            aux1 = data[2]
            aux2 = data[3]
        except:
            aux1 = " "
            aux2 = " "

        if len(aux1) < 3 or len(aux2) < 3:
            msg = send_message(
                message.from_user.id,
                i18n.t("bot.startnewuser", locale=user_lang),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            bot.register_next_step_handler(msg, add_email)
        else:
            send_message(
                message.from_user.id,
                i18n.t("bot.startolduser", locale=user_lang).format(
                    str(u"\U0001F4E4"), data[2], str(u"\U0001F4E5"), data[3]
                ),
                parse_mode="HTML",
                reply_markup=button,
            )

    @bot.message_handler(commands=["email"])
    def ask_email(message):
        user_lang = (message.from_user.language_code or "en-us").lower()
        msg = send_message(
            message.from_user.id, i18n.t("bot.askemail3", locale=user_lang)
        )
        bot.register_next_step_handler(msg, add_email)

    def add_email(message):
        user_lang = (message.from_user.language_code or "en-us").lower()
        set_buttons(user_lang)

        if message.content_type != "text":
            msg = send_message(
                message.from_user.id,
                i18n.t("bot.askemail", locale=user_lang),
                parse_mode="HTML",
            )
            bot.register_next_step_handler(msg, add_email)

            return 0

        try:
            text = message.text.lower()
        except AttributeError:
            text = None

        if text in cmds:
            msg = send_message(
                message.from_user.id, i18n.t("bot.askemail", locale=user_lang)
            )
            bot.register_next_step_handler(msg, add_email)

            return 0
        elif "/" not in message.text:
            if validate_email(message.text.lower()):
                upd_user_email(
                    db,
                    table,
                    message.from_user.id,
                    '"' + str(message.text) + '"',
                )
                data = select_user(db, table, message.from_user.id, "*")

                if "@" not in str(data[3]):
                    msg = send_message(
                        message.chat.id, i18n.t("bot.askemail", locale=user_lang)
                    )
                    bot.register_next_step_handler(msg, add_email)

                    return 0

                if "@" not in str(data[2]):
                    msg = send_message(
                        message.chat.id, i18n.t("bot.askemail2", locale=user_lang)
                    )
                    bot.register_next_step_handler(msg, add_email)

                    return 0

                msg = send_message(
                    message.chat.id,
                    str(u"\U00002705")
                    + i18n.t("bot.success", locale=user_lang),
                    parse_mode="HTML",
                    reply_markup=button,
                )
            else:
                msg = send_message(
                    message.from_user.id,
                    str(u"\U000026A0")
                    + i18n.t("bot.askemail", locale=user_lang),
                    parse_mode="HTML",
                )
                bot.register_next_step_handler(msg, add_email)
        else:
            msg = send_message(
                message.from_user.id,
                i18n.t("bot.askemail", locale=user_lang),
                parse_mode="HTML",
            )
            bot.register_next_step_handler(msg, add_email)

    @bot.message_handler(commands=["send"])
    def ask_file_msg(message):
        user_lang = (message.from_user.language_code or "en-us").lower()
        send_message(
            message.from_user.id, i18n.t("bot.askfile", locale=user_lang)
        )

    def get_file(message):
        user_lang = (message.from_user.language_code or "en-us").lower()

        if str(message.from_user.id) in BLOCKED:

            try:
                logger_info.info(
                    str(datetime.datetime.now())
                    + " BLOCKED: "
                    + str(message.from_user.id)
                    + " "
                    + str(message.message_id)
                    + " "
                    + message.text
                )
            except:
                logger_info.info(
                    str(datetime.datetime.now())
                    + " BLOCKED: "
                    + str(message.from_user.id)
                    + " "
                    + str(message.message_id)
                )

            bot.delete_message(message.from_user.id, message.message_id)

            return 0

        if message.content_type == "document":
            file_size = message.document.file_size
            file_name = message.document.file_name.encode(
                "ASCII", "ignore"
            ).decode("ASCII")
            document = Document(file_name)
            r = redis.Redis(host='localhost', port=6379, db=0)
            r.set(message.chat.id, document.name)
            bot.send_chat_action(message.from_user.id, "upload_document")

            if file_size > 20000000:
                send_message(
                    message.from_user.id,
                    i18n.t("bot.fsize", locale=user_lang),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )

                return 0

            file_info = bot.get_file(message.document.file_id)
            file_url = (
                "https://api.telegram.org/file/bot"
                + TOKEN
                + "/"
                + file_info.file_path
            )
        elif message.content_type == "text":
            if message.text.lower() in cmds:
                send_message(
                    message.from_user.id,
                    i18n.t("bot.askfile", locale=user_lang),
                )

                return 0

            file_url = message.text

            try:
                if message.text[-1] == "/":
                    file_name = message.text.split("/")[-2] + ".pdf"
                else:
                    file_name = message.text.split("/")[-1] + ".pdf"
            except:
                file_name = message.text

            try:
                pdf = weasyprint.HTML(file_url).write_pdf()
                open(file_name, "wb").write(pdf)
            except AssertionError:
                pdf = file_name
            file_url = file_name
        else:
            msg = send_message(
                message.from_user.id, i18n.t("bot.askfile", locale=user_lang)
            )
            bot.register_next_step_handler(msg, get_file)

            return 0

        logger_info.info(
            str(datetime.datetime.now())
            + " FILE: "
            + str(message.from_user.id)
            + " "
            + str(message.message_id)
            + "\t"
            + file_name
        )

        upd_user_file(db, table, message.from_user.id, file_url)
        set_buttons(user_lang)
        if ".pdf" in file_url.lower():
            msg = send_message(
                message.from_user.id,
                i18n.t("bot.askconvert", locale=user_lang),
                parse_mode="HTML",
                reply_markup=button2,
            )
        else:
            data = select_user(db, table, message.from_user.id, "*")
            lang = (message.from_user.language_code or "en-us").lower()
            send_mail(data, '', lang)

    @bot.callback_query_handler(lambda q: q.data == "/converted")
    def ask_conv(call):
        user_lang = (call.from_user.language_code or "en-us").lower()

        try:
            bot.delete_message(call.from_user.id, call.message.id)
        except:
            pass

        try:
            bot.answer_callback_query(call.id)
        except:
            pass

        data = select_user(db, table, call.from_user.id, "*")

        try:
            send_mail(data, 'Convert', user_lang)
        except IndexError:
            msg = send_message(
                call.from_user.id,
                i18n.t("bot.error", locale=user_lang),
                parse_mode="HTML",
            )
            bot.register_next_step_handler(msg, add_email)
            return 0
        except UnicodeEncodeError:
            msg = send_message(
                call.from_user.id,
                i18n.t("bot.error", locale=user_lang),
                parse_mode="HTML",
            )
            bot.register_next_step_handler(msg, add_email)
            return 0

    @bot.callback_query_handler(lambda q: q.data == "/as_is")
    def ask_not_conv(call):
        user_lang = (call.from_user.language_code or "en-us").lower()

        try:
            bot.delete_message(call.from_user.id, call.message.id)
        except:
            pass

        try:
            bot.answer_callback_query(call.id)
        except:
            pass

        data = select_user(db, table, call.from_user.id, "*")
        send_mail(data, '', user_lang)


    @bot.callback_query_handler(lambda q: q.data == "/email")
    def email(call):
        user_lang = (call.from_user.language_code or "en-us").lower()

        try:
            bot.answer_callback_query(call.id)
        except:
            pass

        msg = send_message(
            call.from_user.id, i18n.t("bot.askemail3", locale=user_lang)
        )
        bot.register_next_step_handler(msg, add_email)

    @bot.callback_query_handler(lambda q: q.data == "/send")
    def ask_file_call(call):
        user_lang = (call.from_user.language_code or "en-us").lower()

        try:
            bot.answer_callback_query(call.id)
        except:
            pass

        send_message(
            call.from_user.id, i18n.t("bot.askfile", locale=user_lang)
        )

    @bot.message_handler(func=lambda m: True)
    def generic_msg(message):
        user_lang = (message.from_user.language_code or "en-us").lower()
        #user_lang(message)

        if (
            "@" not in message.text or "/" in message.text
        ) and message.text not in cmds:
            bot.send_chat_action(message.chat.id, "typing")

            try:
                get_file(message)
            except:
                send_message(
                    message.chat.id,
                    i18n.t("bot.filenotfound", locale=user_lang),
                )

    @bot.message_handler(content_types=["document"])
    def generic_file(message):
        user_lang = (message.from_user.language_code or "en-us").lower()
        bot.send_chat_action(message.chat.id, "typing")

        try:
            get_file(message)
        except:
            send_message(
                message.chat.id, i18n.t("bot.filenotfound", locale=user_lang)
            )

    bot.polling()
