import anuncieaqui
import configparser
import datetime
import dns.resolver
import epub_meta
import json
import logging
import logging.handlers
import os
import pika
import redis
import requests
import sqlite3
import subprocess
import time
import urllib.request
import premiumfunctions as premium

import i18n
import telebot
import weasyprint
from bs4 import BeautifulSoup
from flask import Flask, request
from weasyprint import CSS
from weasyprint import HTML
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
CERT = config["DEFAULT"]["CERT"]
PRIVKEY = config["DEFAULT"]["PRIVKEY"]
BLOCKED = config["DEFAULT"]["BLOCKED"]
MULTIPLIER = int(config["DEFAULT"]["MULTIPLIER"])
DEMO = int(config["DEFAULT"]["DEMO"])
ADMIN = int(config["DEFAULT"]["ADMIN"])
db = config["SQLITE3"]["data_base"]
table = config["SQLITE3"]["table"]
rabbitmqcon = config["RABBITMQ"]["CONNECTION_STRING"]

bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

rabbitmq_con = pika.BlockingConnection(pika.URLParameters(rabbitmqcon))
#rabbitmq_con = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
rabbit = rabbitmq_con.channel()
rabbit.queue_declare(queue='Send2KindleBotFast', durable=True)
rabbit.queue_declare(queue='Send2KindleBotSlow', durable=True)

cmds = ["/start", "/send", "/info", "/help", "/email", "/donate", "/stars"]
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

def send_mail(data, subject, lang, file_name):
    msg_sent = send_message(
        data[1], str(u"\U0001F5DE") + i18n.t("bot.sendingfile",
        locale=lang), parse_mode="HTML",
    )
    rabbitmq_con = pika.BlockingConnection(pika.URLParameters(rabbitmqcon))
    #rabbitmq_con = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
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
    file_name = file_name.replace('\n', '')
    msg = (f'{{"from":"{data[2]}", "to":"{data[3]}", "subject":"{subject}", ' 
        f'"user_id":"{data[1]}", "file_url":"{data[7]}", "lang":"{lang}", '
        f'"message_id":"{msg_sent.message_id}", "file_name":"{file_name}"}}')
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

def check_domain(email):
    if 'send.grf.xyz' in email:
        return False
    domain = email.split('@')[-1]
    try:
        dns.resolver.resolve(domain, 'NS')
    except:
        return False
    return True

def send_message(chatid, text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=None):
    try:
        msg = bot.send_message(chatid, text, parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
            reply_markup=reply_markup
        )
        return msg
    except Exception as e:
        raise(e)

def epubauthors(file_path):
    authors = epub_meta.get_epub_metadata(file_path).authors
    return authors

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

def set_menus(user_id, lang='en-us'):
    try:
        bot.set_my_commands([
            telebot.types.BotCommand("/start", i18n.t("bot.btn_start", locale=lang)),
            telebot.types.BotCommand("/stars", i18n.t("bot.btn_stars", locale=lang)),
            telebot.types.BotCommand("/send", i18n.t("bot.btn_send", locale=lang)),
            telebot.types.BotCommand("/tos", i18n.t("bot.btn_tos", locale=lang)),
            telebot.types.BotCommand("/donate", i18n.t("bot.btn_donate", locale=lang)),
            telebot.types.BotCommand("/help", i18n.t("bot.btn_help", locale=lang)),
            telebot.types.BotCommand("/info", i18n.t("bot.btn_info", locale=lang)),
        ], scope=types.BotCommandScopeChat(user_id))
    except:
        pass

def set_buttons(lang='en-us'):
    button = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(
        i18n.t("bot.btn1", locale=lang), callback_data="/send"
    )
    btn2 = types.InlineKeyboardButton(
        i18n.t("bot.btn2", locale=lang), callback_data="/email"
    )
    btn_donate = types.InlineKeyboardButton(
        i18n.t("bot.btn_donate", locale=lang), callback_data="/donate"
    )
    button.row(btn1, btn2)
    button.row(btn_donate)
    button2 = types.InlineKeyboardMarkup()
    btn3 = types.InlineKeyboardButton(
        i18n.t("bot.btn3", locale=lang), callback_data="/as_is"
    )
    btn4 = types.InlineKeyboardButton(
        i18n.t("bot.btn4", locale=lang), callback_data="/converted"
    )
    button2.row(btn3, btn4)
    return button, button2

@bot.message_handler(commands=["help"])
def help(message):
    user_lang = (message.from_user.language_code or "en-us").lower()
    send_message(
        message.from_user.id,
        i18n.t("bot.help", locale=user_lang),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

@bot.message_handler(commands=["saldo"])
def cmd_saldo(message):
    if message.from_user.id != ADMIN:
        return
    try:
        if len(message.text.split(' ')) == 2:
            result = premium.check_premium_user(
                message.text.split(' ')[1]
            )
            saldo = result[0]
        else:
            premium.update_saldo_premium(
                message.text.split(' ')[1],
                message.text.split(' ')[2]
            )
            saldo = message.text.split(' ')[2]
        bot.reply_to(
            message,
            f'🪪 <code>{message.text.split(" ")[1]}</code>\n<b>Saldo</b>: {saldo} envios',
            parse_mode='HTML'
        )
    except:
        bot.delete_message(message.chat.id, message.message_id)

@bot.message_handler(commands=["refund"])
def cmd_refund(message):
    if message.from_user.id != ADMIN:
        return
    if ' ' not in message.text:
        bot.send_message(ADMIN, 'Envie <code>/refund <ID_USUARIO> <ID_TRANSACAO></code>', parse_mode='HTML')
        return
    user_id = message.text.split(' ')[1]
    transaction = message.text.split(' ')[2]
    try:
        refund = bot.refund_star_payment(user_id, transaction)
        bot.send_message(
            ADMIN,
            f'💸 <b>Transação cancelada</b>\n' +
            f'<blockquote expandable>\n' +
            f'<b>Usuário</b>: <code>{user_id}</code>\n' +
            f'<b>ID</b>: {transaction}\n' +
            f'</blockquote>',
            parse_mode='HTML'
        )
    except Exception as e:
        bot.send_message(
            ADMIN,
            f'❌ <b>Transação não encontrada</b>\n<blockquote expandable>{e}</blockquote>',
            parse_mode='HTML'
        )
    bot.delete_message(message.chat.id, message.message_id)

@bot.message_handler(commands=["emails", "dados"])
def cmd_emails(message):
    if message.from_user.id != ADMIN:
        return
    if ' ' not in message.text:
        bot.delete_message(message.from_user.id, message.message_id)
    data = select_user(db, table, message.text.split(' ')[1], "*")
    bot.send_message(
        ADMIN,
        f'🪪 <code>{data[1]}</code>\n<blockquote expandable>' +
        f'<code>📤 {data[2]}\n📥 {data[3]}</code>\n\n🕐 {data[4]}\n🕹 {data[5]}' +
        '</blockquote>',
        parse_mode='HTML'
    )

@bot.message_handler(commands=["relatorio"])
def cmd_relatorio(message):
    if message.from_user.id != ADMIN:
        return
    transactions = bot.get_star_transactions().transactions
    valores_recebidos = 0
    quantidade_recebidos = 0
    valores_devolvidos = 0
    quantidade_devolvidos = 0
    for transaction in transactions:
        if transaction.source:
            valores_recebidos = valores_recebidos + transaction.amount
            quantidade_recebidos = quantidade_recebidos + 1
        elif transaction.receiver:
            valores_devolvidos = valores_devolvidos + transaction.amount
            quantidade_devolvidos = quantidade_devolvidos + 1
    bot.send_message(
        ADMIN,
        f'🗃 <b>Relatório</b>\n' +
        f'<i>{time.strftime("%d/%m/%Y", time.localtime(transactions[0].date))} - ' +
        f'{time.strftime("%d/%m/%Y", time.localtime(transactions[-1].date))}</i>\n\n' +
        '🧮 <b>Quantidades</b>\n' +
        '<blockquote expandable>' +
        f'Recebidos: {quantidade_recebidos}\n' +
        f'Devolvidos: {quantidade_devolvidos}\n' +
        '</blockquote>' +
        f'<b>Saldo</b>: {quantidade_recebidos - quantidade_devolvidos}\n\n' +
        '🌟 <b>Valores</b>\n' +
        '<blockquote expandable>' +
        f'Recebidos:  {valores_recebidos}\n' +
        f'Devolvidos: {valores_devolvidos}\n' +
        '</blockquote>' +
        f'<b>Saldo</b>: {valores_recebidos - valores_devolvidos}',
        parse_mode='HTML'
    )

@bot.message_handler(commands=["lista"])
def cmd_lista(message):
    if message.from_user.id != ADMIN:
        return
    if ' ' not in message.text:
        value = 3
    else:
        value = message.text.split(' ')[1]
    users_list = premium.get_premium_users(value)
    size = len(users_list)
    users = ''
    for user in users_list:
        users = f'{users}<code>{user[1]:<12} {user[2]}</code>\n'
    text = f'<b>Usuários com {value} ou mais estrelas</b>: <blockquote expandable>{users}</blockquote><i>Quantidade: {size}</i>'
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(commands=["tos", "privacy"])
def tos(message):
    user_lang = (message.from_user.language_code or "en-us").lower()
    send_message(
        message.from_user.id,
        i18n.t("bot.tos", locale=user_lang),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

@bot.message_handler(commands=["donate", "pix"])
def tos(message):
    user_lang = (message.from_user.language_code or "en-us").lower()
    bot.send_photo(
        message.from_user.id,
        i18n.t("bot.donate_image", locale=user_lang),
        caption=i18n.t("bot.donate", locale=user_lang),
        parse_mode="HTML",
    )

@bot.message_handler(commands=["info", "paysupport"])
def info(message):
    user_lang = (message.from_user.language_code or "en-us").lower()
    send_message(
        message.from_user.id,
        i18n.t("bot.info", locale=user_lang),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

@bot.message_handler(commands=["stars"])
def cmd_premium(message):
    user_lang = (message.from_user.language_code or "en-us").lower()
    terms_btn = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(
        i18n.t("bot.terms_agree", locale=user_lang), callback_data="/agree"
    )
    btn2 = types.InlineKeyboardButton(
        i18n.t("bot.terms_disagree", locale=user_lang), callback_data="/disagree"
    )
    terms_btn.row(btn1, btn2)
    is_premium = premium.check_premium_user(message.from_user.id)
    if not is_premium:
        send_message(
            message.from_user.id,
            i18n.t("bot.premium_intro", locale=user_lang).format(message.from_user.id, DEMO),
            parse_mode="HTML",
            reply_markup=terms_btn
        )
    else:
        agreed(message)

@bot.callback_query_handler(lambda q: q.data == "/disagree")
def disagreed(call):
    try:
        bot.answer_callback_query(call.id)
    except:
        pass
    try:
        bot.delete_message(call.from_user.id, call.message.id)
    except:
        pass
    start(call)

@bot.callback_query_handler(lambda q: q.data == "/agree")
def agreed(call):
    user_lang = (call.from_user.language_code or "en-us").lower()
    is_premium = premium.check_premium_user(call.from_user.id)
    if not is_premium:
        bot.edit_message_text(
            text=f'{call.message.html_text}',
            chat_id=call.from_user.id,
            message_id=call.message.id,
            parse_mode='HTML'
        )
        premium.add_premium_user(call.from_user.id, DEMO)
        try:
            bot.answer_callback_query(call.id)
        except:
            pass

    values_btn = types.InlineKeyboardMarkup()
    btn5 = types.InlineKeyboardButton(
        '⭐️ 5', callback_data="5"
    )
    btn10 = types.InlineKeyboardButton(
        '⭐️ 10', callback_data="10"
    )
    btn25 = types.InlineKeyboardButton(
        '⭐️ 25', callback_data="25"
    )
    btn50 = types.InlineKeyboardButton(
        '⭐️ 50', callback_data="50"
    )
    btn75 = types.InlineKeyboardButton(
        '⭐️ 75', callback_data="75"
    )
    btn100 = types.InlineKeyboardButton(
        '⭐️ 100', callback_data="100"
    )
    btn_cancel = types.InlineKeyboardButton(
        i18n.t("bot.terms_cancel", locale=user_lang), callback_data="/disagree"
    )
    values_btn.row(btn5, btn10)
    values_btn.row(btn25, btn50)
    values_btn.row(btn75, btn100)
    values_btn.row(btn_cancel)

    bot.send_message(
        call.from_user.id,
        i18n.t("bot.premium_agreed", locale=user_lang).format(call.from_user.id, MULTIPLIER) +
        '\n<blockquote>⭐️ 50 ≈ US$ 0.99</blockquote>',
        reply_markup=values_btn,
        parse_mode='HTML'
    )

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(
        pre_checkout_query.id,
        ok=True,
        error_message='Error. Try again later'
    )

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    payload = int(message.successful_payment.invoice_payload)
    add_value = payload*MULTIPLIER

    is_premium = premium.check_premium_user(message.from_user.id)

    if is_premium:
        saldo = int(is_premium[0])
    else:
        saldo = DEMO

    premium.update_saldo_premium(message.from_user.id, saldo + add_value)
    msg = (
        f'#Stars <code>{message.from_user.id}</code>\n' +
        f'<b>Valor</b>: 🌟{payload}\n' +
        '<blockquote expandable>' +
        f'<b>Envios</b>: {add_value}\n<b>Saldo</b>: {saldo+add_value}\n\n' +
        f'<b>Telegram Payment ChargeID</b>:\n' +
        f'<code>{message.successful_payment.telegram_payment_charge_id}</code>' +
        '</blockquote>'
    )
    bot.send_message(
        ADMIN,
        msg,
        parse_mode='HTML'
    )
    start(message)

@bot.message_handler(commands=["start"])
def start(message):
    user_lang = (message.from_user.language_code or "en-us").lower()
    button, button2 = set_buttons(user_lang)
    set_menus(message.from_user.id, user_lang)
    data = select_user(db, table, message.from_user.id, "*")
    is_premium = premium.check_premium_user(message.from_user.id)
    if is_premium:
        saldo = int(is_premium[0])
    else:
        saldo = 0

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
        msg = (
            i18n.t(
                "bot.startolduser",
                locale=user_lang
            ).format(
                str(u"\U0001F4E4"),
                data[2],
                str(u"\U0001F4E5"),
                data[3]
            )
        )
        if saldo:
            msg = f'{msg}\n<b>{i18n.t("bot.balance", locale=user_lang)}</b>: {saldo}'

        send_message(
            message.from_user.id,
            msg,
            parse_mode="HTML",
            reply_markup=button,
        )
        try:
            if 'stars' in message.text:
                cmd_premium(message)
        except:
            pass

@bot.message_handler(commands=["email"])
def ask_email(message):
    user_lang = (message.from_user.language_code or "en-us").lower()
    msg = send_message(
        message.from_user.id, i18n.t("bot.askemail3", locale=user_lang)
    )
    bot.register_next_step_handler(msg, add_email)

def add_email(message):
    user_lang = (message.from_user.language_code or "en-us").lower()
    button, button2 = set_buttons(user_lang)

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
        if validate_email(message.text.lower()) and check_domain(message.text.lower()):
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
        bot.delete_message(message.from_user.id, message.message_id)
        return 0

    if message.content_type == "document":
        file_size = message.document.file_size
        try:
            file_name = message.document.file_name.encode(
                "ASCII", "ignore"
            ).decode("ASCII")
        except Exception as e:
            raise(e)

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
        elif '.onion' in message.text.lower():
            bot.delete_message(message.from_user.id, message.message_id)
            return 0

        file_url = message.text

        try:
            response = requests.get(file_url, headers = {'User-agent': 'Mozilla/5.1'}, timeout=300)
        except Exception as e:
            raise(e)
        file_html = BeautifulSoup(response.content, 'html.parser', from_encoding="utf-8")
        try:
            title = file_html.find('meta', {'property': 'og:title'})
        except:
            title = file_html.find('title')
        try:
            file_name = f'files/{title["content"]} {message.from_user.id}.pdf'
        except:
            file_name = f'files/{message.from_user.id}.pdf'
        try:
            file_name = file_name.encode("ASCII", "ignore").decode("ASCII")
        except Exception as e:
            raise(e)
        pid = subprocess.Popen([
            'python3', 'loop_upload_action.py', str(message.from_user.id)
        ])
        try:
            pdf = HTML(string=str(file_html)).write_pdf()
            open(file_name, 'wb').write(pdf)
        except AttributeError:
            css = CSS(string='@page { size: A5; margin: 1cm }')
            pdf = HTML(string=str(file_html)).write_pdf(stylesheets=[css])
            open(file_name, 'wb').write(pdf)
        except AssertionError:
            pdf = file_name
        subprocess.Popen([
            'kill', str(pid.pid)
        ])
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
    button, button2 = set_buttons(user_lang)
    if '.' not in file_name:
        send_message(
            message.chat.id,
            i18n.t("bot.filenotfound", locale=user_lang),
        )
    elif ".pdf" in file_url.lower():
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.set(message.chat.id, file_name)
        msg = send_message(
            message.from_user.id,
            i18n.t("bot.askconvert", locale=user_lang),
            parse_mode="HTML",
            reply_markup=button2,
        )
    else:
        data = select_user(db, table, message.from_user.id, "*")
        lang = (message.from_user.language_code or "en-us").lower()
        interval = (
            datetime.datetime.now()
            - datetime.datetime.strptime(
                data[5], "%Y-%m-%d %H:%M:%S.%f"
            )
        ).total_seconds()
        #if interval > 5:
        send_mail(data, '', lang, file_name)

@bot.callback_query_handler(lambda q: q.data == "/converted")
def ask_conv(call):
    user_lang = (call.from_user.language_code or "en-us").lower()

    r = redis.Redis(host='localhost', port=6379, db=0)
    file_name = r.get(call.from_user.id).decode('utf-8')

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
        send_mail(data, 'Convert', user_lang, file_name)
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

@bot.callback_query_handler(lambda q: q.data == "/donate")
def callback_donate(call):
    user_lang = (call.from_user.language_code or "en-us").lower()
    bot.send_photo(
        call.from_user.id,
        i18n.t("bot.donate_image", locale=user_lang),
        caption=i18n.t("bot.donate", locale=user_lang),
        parse_mode="HTML",
    )
    try:
        bot.answer_callback_query(call.id)
    except:
        pass

@bot.callback_query_handler(lambda q: q.data == "/as_is")
def ask_not_conv(call):
    user_lang = (call.from_user.language_code or "en-us").lower()
       
    r = redis.Redis(host='localhost', port=6379, db=0)
    file_name = r.get(call.from_user.id).decode('utf-8')

    try:
        bot.delete_message(call.from_user.id, call.message.id)
    except:
        pass

    try:
        bot.answer_callback_query(call.id)
    except:
        pass

    data = select_user(db, table, call.from_user.id, "*")
    send_mail(data, '', user_lang, file_name)


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

    if (
        "@" not in message.text or "/" in message.text
    ) and message.text not in cmds:

        try:
            get_file(message)
        except:
            send_message(
                message.chat.id,
                i18n.t("bot.filenotfound", locale=user_lang),
            )
    elif '@' in message.text:
        add_email(message)

@bot.message_handler(content_types=["document"])
def generic_file(message):
    user_lang = (message.from_user.language_code or "en-us").lower()
    set_menus(message.from_user.id, user_lang)

    try:
        get_file(message)
    except:
        send_message(
            message.chat.id, i18n.t("bot.filenotfound", locale=user_lang)
        )

@bot.callback_query_handler(func=lambda q:True)
def value_picked(call):
    try:
        bot.delete_message(call.from_user.id, call.message.id)
    except:
        pass
    try:
        bot.answer_callback_query(call.id)
    except:
        pass
    user_lang = (call.from_user.language_code or "en-us").lower()
    is_premium = premium.check_premium_user(call.from_user.id)
    value = int(call.data)
    bot.send_invoice(
        call.from_user.id,
        provider_token=None,
        title=i18n.t("bot.payment_title", locale=user_lang).format(value*MULTIPLIER),
        description=i18n.t("bot.payment_description", locale=user_lang).format(value, value*MULTIPLIER, call.from_user.id),
        currency='XTR',
        prices=[
            telebot.types.LabeledPrice(
                label=f'{value}',
                amount=value
            )
        ],
        start_parameter=f'star{value}',
        invoice_payload=f'{value}'
    )

@server.route(f'/{TOKEN}', methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

if __name__ == "__main__":
    bot.infinity_polling()
    #server.run(host="0.0.0.0", port=443, ssl_context=(f'{CERT}', f'{PRIVKEY}'))
