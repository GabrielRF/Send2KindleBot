import anuncieaqui
import configparser
import dns.resolver
import ebooklib
import i18n
import pika
import json
import os
import random
import signal
import smtplib
import subprocess
import sqlite3
import sys
import telebot
import urllib.request
import premiumfunctions as premium
from ebooklib import epub
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from telebot import types

BOT_CONFIG_FILE = "kindle.conf"
config = configparser.ConfigParser()
config.sections()
config.read(BOT_CONFIG_FILE)
TOKEN = config["DEFAULT"]["TOKEN"]
rabbitmqcon = config["RABBITMQ"]["CONNECTION_STRING"]

effects = [
    5107584321108051014,
    5104841245755180586,
    5046509860389126442
]

def send_message(chatid, text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=None, message_effect_id=None):
    try:
        msg = bot.send_message(chatid, text, parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
            reply_markup=reply_markup,
            message_effect_id=message_effect_id
        )
    except:
        pass

def open_file(file_url, user_id, original_file_name):
    if "api.telegram.org/file" not in file_url:
        return f'{file_url}'
    file_name, headers = urllib.request.urlretrieve(
        file_url, f'files/{file_url.split("/")[-1]}'
    )

    new_file_name = (
        f'files/{os.path.splitext(original_file_name)[0]}.{file_name.split(".")[-1]}'
    )
    os.rename(file_name, new_file_name)

    return new_file_name

def convert_format(file_name_original, user_id):
    try:
        bot.send_chat_action(user_id, "upload_document")
    except:
        pass
    file_name_converted = file_name_original.replace(
        file_name_original.split(".")[-1], "epub"
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


def process_file(files, user_id):
    if (
            ".mobi" in files[-5:]
            or ".cbr" in files[-5:]
            or ".cbz" in files[-5:]
            or ".azw" in files[-5:]
            or ".prc" in files[-5:]
            or ".azw3" in files[-5:]
        ):
        files = convert_format(files, user_id)
    return files

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

def check_domain(email):
    domain = email.split('@')[-1]
    try:
        dns.resolver.resolve(domain)
    except:
        return False
    return True

def send_file(rbt, method, properties, data):
    rbt.basic_ack(delivery_tag=method.delivery_tag)
    data = json.loads(data)
    msg = MIMEMultipart()

    try:
        bot.send_chat_action(data['user_id'], 'upload_document')
    except:
        pass

    is_premium = premium.check_premium_user(data['user_id'])

    if is_premium:
        saldo = int(is_premium[0])
    else:
        saldo = 0

    if saldo > 0:
        msg["From"] = f'{data["user_id"]}@send.grf.xyz'
    else:
        msg["From"] = f"{data['from']}"

    msg["To"] = f"{data['to']}"
    msg["Date"] = formatdate(localtime=True)
    msg["Subject"] = f"{data['subject']}"
    text = f"Send2KindleBot - Document sent from Telegram user {data['user_id']}"

    msg.attach(MIMEText(text.format(data['user_id'])))

    if not check_domain(data['to']) or not check_domain(data['from']):
        send_message(
            data['user_id'],
            i18n.t("bot.checkemail", locale=data['lang']),
        )
        return

    try:
        files = open_file(data['file_url'], data['user_id'], data['file_name'])
        files = process_file(files, data['user_id'])
    except:
        send_message(
            data['user_id'],
            i18n.t("bot.filenotfound", locale=data['lang']),
        )
        return

    part = MIMEBase("application", "octet-stream")
    part.set_payload(open(files, "rb").read())
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        'attachment; filename="{0}"'.format(os.path.basename(files)),
    )
    msg.attach(part)
    smtp = smtplib.SMTP("127.0.0.1")
    try:
        smtp.sendmail(msg['From'], msg['To'], msg.as_string())
    except smtplib.SMTPSenderRefused:
        msg = send_message(
            data['user_id'],
            str(u"\U000026A0") + i18n.t("bot.fsize", locale=data['lang']),
            parse_mode="HTML",
        )
    except smtplib.SMTPRecipientsRefused:
        msg = send_message(
            data['user_id'],
            str(u"\U000026A0") + i18n.t("bot.checkemail", locale=data['lang']),
            parse_mode="HTML",
        )
    smtp.close()

    try:
        os.remove(files)
    except FileNotFoundError:
        pass

    try:
        bot.delete_message(data['user_id'], data['message_id'])
    except:
        pass

    set_buttons(data['lang'])
    msg = ("{icon_x} {msg_a}").format(
        icon_x=u"\U0001F4EE",
        msg_a=i18n.t("bot.filesent", locale=data['lang']),
    )
    if saldo:
        msg = f'{msg}\n<b>{i18n.t("bot.balance", locale=data["lang"])}</b>: {saldo - 1}'
    if 'pt-br' in data['lang']:
        try:
            anuncieaqui.send_message(TOKEN, data['user_id'], msg, random.choice(effects))
        except:
            send_message(
                data['user_id'],
                msg,
                parse_mode="HTML",
                reply_markup=button,
                disable_web_page_preview=True,
                message_effect_id=random.choice(effects)
            )
    else:
        if not random.randint(0,7):
            msg = f'{msg}\n\n/donate'
        send_message(
            data['user_id'],
            msg,
            parse_mode="HTML",
            reply_markup=button,
            disable_web_page_preview=True,
            message_effect_id=random.choice(effects)
        )
    if saldo:
        premium.update_saldo_premium(data['user_id'], saldo-1)

if __name__ == "__main__":
    i18n.load_path.append("i18n")
    i18n.set("fallback", "en-us")
    bot = telebot.TeleBot(TOKEN)
    rabbitmq_con = pika.BlockingConnection(pika.URLParameters(rabbitmqcon))
    #rabbitmq_con = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    rabbit = rabbitmq_con.channel()
    rabbit.basic_qos(prefetch_count=1)
    rabbit.basic_consume(queue=sys.argv[1], on_message_callback=send_file)
    rabbit.start_consuming()
