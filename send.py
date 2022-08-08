import configparser
import pika
import json
import os
import random
import smtplib
import subprocess
import sqlite3
import telebot
import urllib.request
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

def open_file(file_url, user_id):
    if "api.telegram.org/file" not in file_url:
        return file_url
    try:
        try:
            r = redis.Redis(host='localhost', port=6379, db=0)
            fname = r.get(user_id).decode('utf-8')
            r.delete(user_id)
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
        os.path.splitext(file_name)[0] + "." + file_name.split(".")[-1]
    )
    os.rename(file_name, new_file_name)

    return new_file_name

def convert_format(file_name_original, user_id):
    bot.send_chat_action(user_id, "upload_document")
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


def process_file(files, user_id):
    if '.epub' in files:
        try:
            doc = epub.read_epub(files)
            doc.set_identifier(user_id)
            epub.write_epub(files, doc)
        except:
            pass
    else:
        files = convert_format(files, user_id)

def should_convert(files):
    if (
        ".mobi" in files
        or ".cbr" in files
        or ".cbz" in files
        or ".azw3" in files
    ):
        return random.randint(0,10)
    else:
        return True

def send_file(rbt, method, properties, data):
    data=data
    data = json.loads(data)

    msg = MIMEMultipart()
    msg["From"] = f"{data['from']}"
    msg["To"] = f"{data['to']}"
    msg["Date"] = formatdate(localtime=True)
    msg["Subject"] = f"{data['subject']}"
    text = f"Send2KindleBot - Document sent from Telegram user {data['user_id']}"

    msg.attach(MIMEText(text.format(data['user_id'])))

    files = open_file(data['file_url'], data['user_id'])
    if not should_convert(files):
        exit()
    process_file(files, data['user_id'])
    rbt.basic_ack(delivery_tag=method.delivery_tag)

    # Definir files
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
        smtp.sendmail(send_from, send_to, msg.as_string())
    except smtplib.SMTPSenderRefused:
        msg = send_message(
            data['user_id'],
            str(u"\U000026A0") + i18n.t("bot.fsize", locale=lang),
            parse_mode="HTML",
        )
    except smtplib.SMTPRecipientsRefused:
        msg = send_message(
            data['user_id'],
            str(u"\U000026A0") + i18n.t("bot.checkemail", locale=user_lang),
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

    set_buttons(lang)
    msg = ("{icon_x} {msg_a}").format(
        icon_x=u"\U0001F4EE",
        msg_a=i18n.t("bot.filesent", locale=lang),
    )
    bot.send_message(
        user_id,
        msg,
        parse_mode="HTML",
        reply_markup=button,
        disable_web_page_preview=True,
    )

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.sections()
    BOT_CONFIG_FILE = "kindle.conf"
    config.read(BOT_CONFIG_FILE)
    TOKEN = config["DEFAULT"]["TOKEN"]
    bot = telebot.TeleBot(TOKEN)
    rabbitmq_con = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    rabbit = rabbitmq_con.channel()
    rabbit.basic_qos(prefetch_count=1)
    rabbit.basic_consume(queue='Send2KindleBot', on_message_callback=send_file)
    rabbit.start_consuming()
