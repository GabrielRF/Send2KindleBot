import configparser
import datetime
import logging
import logging.handlers
import os
import smtplib
import sqlite3
import subprocess
import urllib.request
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

import i18n
import sentry_sdk
import telebot
import weasyprint
from telebot import types
from validate_email import validate_email

i18n.load_path.append("i18n")
i18n.set("fallback", "en-us")

document_dict = {}


class Document:
    def __init__(self, name):
        self.name = name


def epub2mobi(file_name_epub, chatid):
    logger_info.info(
        str(datetime.datetime.now())
        + " CONVERT: "
        + str(chatid)
        + " "
        + file_name_epub
    )
    bot.send_chat_action(chatid, "upload_document")
    file_name_mobi = file_name_epub.replace(
        file_name_epub.split(".")[-1], ".mobi"
    )

    if ".cbr" in file_name_epub or ".cbz" in file_name_epub:
        subprocess.Popen(
            [
                "ebook-convert",
                file_name_epub,
                file_name_mobi,
                "--output-profile",
                "tablet",
            ]
        ).wait()
    else:
        subprocess.Popen(
            ["ebook-convert", file_name_epub, file_name_mobi]
        ).wait()

    os.remove(file_name_epub)

    return file_name_mobi


# Get file from URL
def open_file(file_url, chatid):
    if "api.telegram.org/file" not in file_url:
        return file_url

    print(file_url)

    try:
        if ".pdf" in file_url:
            fname = document_dict[str(chatid)]
            file_name, headers = urllib.request.urlretrieve(
                file_url, fname.name
            )
        else:
            file_name, headers = urllib.request.urlretrieve(
                file_url, file_url.split("/")[-1]
            )
    except KeyError:
        file_name, headers = urllib.request.urlretrieve(
            file_url, file_url.split("/")[-1]
        )

    new_file_name = (
        os.path.splitext(file_name)[0][:20] + "." + file_name.split(".")[-1]
    )
    print(new_file_name)
    os.rename(file_name, new_file_name)

    return new_file_name


# Send e-mail function
def send_mail(
    chatid, send_from, send_to, subject, text, file_url, last_usage, user_lang
):
    set_buttons(user_lang)

    try:
        interval = (
            datetime.datetime.now()
            - datetime.datetime.strptime(last_usage, "%Y-%m-%d %H:%M:%S.%f")
        ).total_seconds()
    except ValueError:
        interval = 901

    if len(send_from) < 5 or len(send_to) < 5:
        bot.send_message(
            chatid, i18n.t("bot.error", locale=user_lang), parse_mode="HTML"
        )

        return 0

    msg = MIMEMultipart()
    msg["From"] = send_from
    msg["To"] = send_to
    msg["Date"] = formatdate(localtime=True)
    msg["Subject"] = subject

    msg.attach(MIMEText("Send2KindleBot"))

    try:
        files = open_file(file_url, chatid)
        upd_user_last(db, table, chatid)

        if (
            ".epub" in files
            or ".cbr" in files
            or ".cbz" in files
            or ".azw3" in files
        ):
            if interval < 900 and "9083329" not in chatid:
                try:
                    bot.send_message(
                        chatid, i18n.t("bot.slowmode", locale=user_lang)
                    )
                except:
                    bot.send_message(chatid, "Wait 15 minutes")

                os.remove(files)

                return 0
            else:
                files = epub2mobi(files, chatid)
    except:
        bot.send_message(chatid, i18n.t("bot.filenotfound", locale=user_lang))
        return 0

    bot.send_chat_action(chatid, "upload_document")
    bot.send_message(
        chatid,
        str(u"\U0001F5DE") + i18n.t("bot.sendingfile", locale=user_lang),
        parse_mode="HTML",
    )
    bot.send_chat_action(chatid, "upload_document")

    try:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(open(files, "rb").read())
        encoders.encode_base64(part)
    except FileNotFoundError:
        bot.send_message(chatid, i18n.t("bot.filenotfound", locale=user_lang))

    part.add_header(
        "Content-Disposition",
        'attachment; filename="{0}"'.format(os.path.basename(files)),
    )
    msg.attach(part)

    smtp = smtplib.SMTP("127.0.0.1")

    try:
        smtp.sendmail(send_from, send_to, msg.as_string())
    except smtplib.SMTPSenderRefused:
        print("Erro")
        msg = bot.send_message(
            chatid,
            str(u"\U000026A0") + i18n.t("bot.fsize", locale=user_lang),
            parse_mode="HTML",
        )
        smtp.close()
        logger_info.info(
            str(datetime.datetime.now())
            + "\tError:\t"
            + str(chatid)
            + "\t"
            + send_from
            + "\t"
            + send_to
        )

        try:
            os.remove(files)
        except FileNotFoundError:
            pass

        return 0
    except smtplib.SMTPRecipientsRefused:
        msg = bot.send_message(
            chatid,
            str(u"\U000026A0") + i18n.t("bot.checkemail", locale=user_lang),
            parse_mode="HTML",
        )
        smtp.close()
        logger_info.info(
            str(datetime.datetime.now())
            + "\tError:\t"
            + str(chatid)
            + "\t"
            + send_from
            + "\t"
            + send_to
        )

        try:
            os.remove(files)
        except FileNotFoundError:
            pass

        return 0

    smtp.close()

    upd_user_last(db, table, chatid)

    logger_info.info(
        str(datetime.datetime.now())
        + " SENT: "
        + str(chatid)
        + "\t"
        + send_from
        + "\t"
        + send_to
        + "\t "
        + files
    )

    try:
        os.remove(files)
    except FileNotFoundError:
        pass

    msg = ("{icon_x} {msg_a}\n\n" "{icon_z} {msg_c}").format(
        icon_x=u"\U0001F4EE",
        icon_z=u"\U0001F4B5",
        msg_a=i18n.t("bot.filesent", locale=user_lang),
        msg_c=i18n.t("bot.donate", locale=user_lang),
    )
    bot.send_message(
        chatid,
        msg,
        parse_mode="HTML",
        reply_markup=button,
        disable_web_page_preview=True,
    )


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
    config = configparser.ConfigParser()
    config.sections()
    BOT_CONFIG_FILE = "/usr/local/bin/Send2KindleBot/kindle.conf"
    config.read(BOT_CONFIG_FILE)
    log_file = config["DEFAULT"]["logfile"]
    TOKEN = config["DEFAULT"]["TOKEN"]
    BLOCKED = config["DEFAULT"]["BLOCKED"]
    db = config["SQLITE3"]["data_base"]
    table = config["SQLITE3"]["table"]

    bot = telebot.TeleBot(TOKEN)
    cmds = ["/start", "/send", "/info", "/help", "/email"]
    LOG_INFO_FILE = log_file
    logger_info = logging.getLogger("InfoLogger")
    logger_info.setLevel(logging.DEBUG)
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
        bot.send_message(
            message.from_user.id,
            i18n.t("bot.help", locale=user_lang),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

    @bot.message_handler(commands=["tos"])
    def tos(message):
        user_lang = (message.from_user.language_code or "en-us").lower()
        bot.send_message(
            message.from_user.id,
            i18n.t("bot.tos", locale=user_lang),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

    @bot.message_handler(commands=["info"])
    def info(message):
        user_lang = (message.from_user.language_code or "en-us").lower()
        bot.send_message(
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

        try:
            aux1 = data[2]
            aux2 = data[3]
        except:
            aux1 = " "
            aux2 = " "

        if len(aux1) < 3 or len(aux2) < 3:
            msg = bot.send_message(
                message.from_user.id,
                i18n.t("bot.startnewuser", locale=user_lang),
                parse_mode="HTML",
            )
            bot.register_next_step_handler(msg, add_email)
        else:
            bot.send_message(
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
        msg = bot.send_message(
            message.from_user.id, i18n.t("bot.askemail3", locale=user_lang)
        )
        bot.register_next_step_handler(msg, add_email)

    def add_email(message):
        user_lang = (message.from_user.language_code or "en-us").lower()

        if message.content_type != "text":
            msg = bot.send_message(
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
            msg = bot.send_message(
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
                    msg = bot.reply_to(
                        message, i18n.t("bot.askemail", locale=user_lang)
                    )
                    bot.register_next_step_handler(msg, add_email)

                    return 0

                if "@" not in str(data[2]):
                    msg = bot.reply_to(
                        message, i18n.t("bot.askemail2", locale=user_lang)
                    )
                    bot.register_next_step_handler(msg, add_email)

                    return 0

                msg = bot.reply_to(
                    message,
                    str(u"\U00002705")
                    + i18n.t("bot.success", locale=user_lang),
                    parse_mode="HTML",
                    reply_markup=button,
                )
            else:
                msg = bot.send_message(
                    message.from_user.id,
                    str(u"\U000026A0")
                    + i18n.t("bot.askemail", locale=user_lang),
                    parse_mode="HTML",
                )
                bot.register_next_step_handler(msg, add_email)
        else:
            msg = bot.send_message(
                message.from_user.id,
                i18n.t("bot.askemail", locale=user_lang),
                parse_mode="HTML",
            )
            bot.register_next_step_handler(msg, add_email)

    @bot.message_handler(commands=["send"])
    def ask_file_msg(message):
        user_lang = (message.from_user.language_code or "en-us").lower()
        bot.send_message(
            message.from_user.id, i18n.t("bot.askfile", locale=user_lang)
        )

    def get_file(message):
        user_lang = (message.from_user.language_code or "en-us").lower()

        if str(message.from_user.id) in BLOCKED:
            print(message)

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
            document_dict[str(message.from_user.id)] = document
            bot.reply_to(
                message,
                str(u"\U00002705")
                + "Downloaded "
                + str(file_size)
                + " bytes.",
            )
            bot.send_chat_action(message.from_user.id, "upload_document")

            if file_size > 20000000:
                bot.send_message(
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
                bot.send_message(
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

            pdf = weasyprint.HTML(file_url).write_pdf()
            open(file_name, "wb").write(pdf)
            file_url = file_name
        else:
            msg = bot.send_message(
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

        if ".pdf" in file_url.lower():
            msg = bot.send_message(
                message.from_user.id,
                i18n.t("bot.askconvert", locale=user_lang),
                parse_mode="HTML",
                reply_markup=button2,
            )
        else:
            data = select_user(db, table, message.from_user.id, "*")
            lang = (message.from_user.language_code or "en-us").lower()
            send_mail(
                str(message.from_user.id),
                data[2],
                data[3],
                " ",
                str(message.from_user.id),
                data[7],
                data[5],
                lang,
            )

    @bot.callback_query_handler(lambda q: q.data == "/converted")
    def ask_conv(call):
        user_lang = (call.from_user.language_code or "en-us").lower()

        try:
            bot.answer_callback_query(call.id)
        except:
            pass

        data = select_user(db, table, call.from_user.id, "*")

        try:
            send_mail(
                str(call.from_user.id),
                data[2],
                data[3],
                "Convert",
                str(call.from_user.id),
                data[7],
                data[5],
                user_lang,
            )
        except IndexError:
            msg = bot.send_message(
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
            bot.answer_callback_query(call.id)
        except:
            pass

        data = select_user(db, table, call.from_user.id, "*")
        send_mail(
            str(call.from_user.id),
            data[2],
            data[3],
            " ",
            str(call.from_user.id),
            data[7],
            data[5],
            user_lang,
        )

    @bot.callback_query_handler(lambda q: q.data == "/email")
    def email(call):
        user_lang = (call.from_user.language_code or "en-us").lower()

        try:
            bot.answer_callback_query(call.id)
        except:
            pass

        msg = bot.send_message(
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

        bot.send_message(
            call.from_user.id, i18n.t("bot.askfile", locale=user_lang)
        )

    @bot.message_handler(func=lambda m: True)
    def generic_msg(message):
        user_lang = (message.from_user.language_code or "en-us").lower()
        user_lang(message)

        if (
            "@" not in message.text or "/" in message.text
        ) and message.text not in cmds:
            bot.send_chat_action(message.chat.id, "typing")

            try:
                get_file(message)
            except:
                bot.send_message(
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
            bot.send_message(
                message.chat.id, i18n.t("bot.filenotfound", locale=user_lang)
            )

    sentry_url = config["SENTRY"]["url"]

    if sentry_url:
        sentry_sdk.init(sentry_url)

    bot.polling()
