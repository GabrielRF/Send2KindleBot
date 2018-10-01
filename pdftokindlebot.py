import configparser
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders
import i18n
import logging
import logging.handlers
import os
# import requests
import smtplib
import sqlite3
# import sys
import telebot
from telebot import types
import urllib.request
from validate_email import validate_email


i18n.load_path.append('i18n')
i18n.set('locale', 'en-us')

# Get file from URL
def open_file(file_url, chatid):

    file_name, headers = urllib.request.urlretrieve(file_url, 
        'send2kindle_' + file_url.split('/')[-1])
    return file_name


# Send e-mail function
def send_mail(chatid, send_from, send_to, subject, text, file_url):
    if len(send_from) < 5 or len(send_to) < 5:
        bot.send_message(chatid, i18n.t('bot.error'), parse_mode='HTML')
        return 0
    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = send_to
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(MIMEText('Send2KindleBot'))

    try:
        files = open_file(file_url, chatid)
    except:
        bot.send_message(chatid, i18n.t('bot.filenotfound'))
        return 0

    bot.send_chat_action(chatid, 'upload_document')
    bot.send_message(chatid, str(u'\U0001F5DE')
        + i18n.t('bot.sendingfile'), parse_mode='HTML')

    part = MIMEBase('application', 'octet-stream')
    part.set_payload(open(files, 'rb').read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition',
        'attachment; filename="{0}"'.format(os.path.basename(files)))
    msg.attach(part)

    smtp = smtplib.SMTP('127.0.0.1')

    try:
        smtp.sendmail(send_from, send_to, msg.as_string())
    except smtplib.SMTPRecipientsRefused:
        msg = bot.send_message(chatid,
            str(u'\U000026A0') + i18n.t('bot.checkemail'), parse_mode='HTML')
        smtp.close()
        logger_info.info(str(datetime.datetime.now()) + '\tError:\t'
            + str(chatid) + '\t' + send_from + '\t' + send_to)
        upd_user_last(db, table, chatid)
        return 0

    smtp.close()

    upd_user_last(db, table, chatid)

    logger_info.info(str(datetime.datetime.now()) + '\tSENT:\t' + str(chatid)
        + '\t' + send_from + '\t' + send_to)
    try:
        os.remove(files)
    except FileNotFoundError:
        pass
    msg = (
        '{icon_x} {msg_a}\n\n'
        '{icon_y} {msg_b}\n\n'
        '{icon_z} {msg_c}'
    ).format(
        icon_x=u'\U0001F4EE',
        icon_y=u'\U00002B50',
        icon_z=u'\U0001F4B5',
        msg_a=i18n.t('bot.filesent'),
        msg_b=i18n.t('bot.rate'),
        msg_c=i18n.t('bot.donate'),
    )
    bot.send_message(chatid, msg, parse_mode='HTML',
        reply_markup=button, disable_web_page_preview=True)


# Add user to database
def add_user(db, table, chatid):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    aux = ('''INSERT INTO {} (chatid, remetente, destinatario, criacao, usado)
        VALUES ('{}', '', '',
        '{}', '{}')''').format(table, chatid,
        str(datetime.datetime.now()), str(datetime.datetime.now()))
    logger_info.info(str(datetime.datetime.now()) + '\tUSER:\t' + str(chatid))
    cursor.execute(aux)
    conn.commit()
    conn.close()


# Update user last usage
def upd_user_last(db, table, chatid):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    aux = ('''UPDATE {} SET usado = {}
        WHERE chatid = {}''').format(table, '"' + str(datetime.datetime.now())
        + '"', chatid)
    cursor.execute(aux)
    conn.commit()
    conn.close()
    # logger_info.info(str(datetime.datetime.now()) + '\tLAST:\t'
    #   + str(chatid))

def upd_user_file(db, table, chatid, file_url):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    aux = ('''UPDATE {} SET arquivo = {}
        WHERE chatid = {}''').format(table, '"' + file_url + '"', chatid)
    cursor.execute(aux)
    conn.commit()
    conn.close()

# Update user e-mail
def upd_user_email(db, table, chatid, email):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    if '@kindle.' in email.lower():
        aux = ('''UPDATE {} SET destinatario = {}
            WHERE chatid = {}''').format(table, email, chatid)
    else:
        aux = ('''UPDATE {} SET remetente = {}
            WHERE chatid = {}''').format(table, email, chatid)
    # print(aux)
    logger_info.info(str(datetime.datetime.now()) + '\tUPD:\t' + str(chatid)
        + '\t' + email)
    cursor.execute(aux)
    conn.commit()
    conn.close()


# Select user on database
def select_user(db, table, chatid, field):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    aux = ('''SELECT {} FROM "{}" WHERE
        chatid="{}"''').format(field, table, chatid)
    cursor.execute(aux)
    usuarios = cursor.fetchone()
    if usuarios:
        data = usuarios
    else:
        add_user(db, table, chatid)
        data = ''
    conn.close()
    return data

def user_lang(message):
    try:
        user_lang = message.from_user.language_code.lower()
    except:
        user_lang = 'en-us'
    print(user_lang)
    i18n.set('locale', user_lang)
    i18n.set('fallback', 'en-us')
    set_buttons()


def set_buttons():
    global button
    global button2
    button = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(i18n.t('bot.btn1'), callback_data='/send')
    btn2 = types.InlineKeyboardButton(i18n.t('bot.btn2'), callback_data='/email')
    button.row(btn1, btn2)
    button2 = types.InlineKeyboardMarkup()
    btn3 = types.InlineKeyboardButton(i18n.t('bot.btn3'), callback_data='/as_is')
    btn4 = types.InlineKeyboardButton(i18n.t('bot.btn4'), callback_data='/converted')
    button2.row(btn3, btn4)


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.sections()
    BOT_CONFIG_FILE = '/usr/local/bin/Send2KindleBot/kindle.conf'
    config.read(BOT_CONFIG_FILE)
    log_file = config['DEFAULT']['logfile']
    TOKEN = config['DEFAULT']['TOKEN']
    db = config['SQLITE3']['data_base']
    table = config['SQLITE3']['table']

    bot = telebot.TeleBot(TOKEN)
    cmds = ['/start', '/send', '/info', '/help']
    LOG_INFO_FILE = log_file
    logger_info = logging.getLogger('InfoLogger')
    logger_info.setLevel(logging.DEBUG)
    handler_info = logging.handlers.TimedRotatingFileHandler(LOG_INFO_FILE,
        when='midnight', interval=1, backupCount=7, encoding='utf-8')
    logger_info.addHandler(handler_info)


    @bot.message_handler(commands=['help'])
    def help(message):
        user_lang(message)
        bot.send_message(message.from_user.id, i18n.t('bot.help'), parse_mode='HTML', 
            disable_web_page_preview=True)


    @bot.message_handler(commands=['info'])
    def help(message):
        user_lang(message)
        bot.send_message(message.from_user.id, i18n.t('bot.info'), parse_mode='HTML', 
            disable_web_page_preview=True)


    # select_user(db, table, sys.argv[1])
    @bot.message_handler(commands=['start'])
    def start(message):
        user_lang(message)
        data = select_user(db, table, message.from_user.id, '*')
        try:
            aux1 = data[2]
            aux2 = data[3]
        except:
            aux1 = ' '
            aux2 = ' '
        if len(aux1) < 3 or len(aux2) < 3:
            msg = bot.send_message(message.from_user.id,
                i18n.t('bot.startnewuser'), parse_mode='HTML')
            bot.register_next_step_handler(msg, add_email)
        else:
            bot.send_message(message.from_user.id,
                i18n.t('bot.startolduser').format(
                str(u'\U0001F4E4'), data[2], str(u'\U0001F4E5'), data[3]
            ), parse_mode='HTML', reply_markup=button)

    @bot.message_handler(commands=['email'])
    def ask_email(message):
        user_lang(message)
        msg = bot.send_message(message.from_user.id, i18n.t('bot.askemail'))
        bot.register_next_step_handler(msg, add_email)

    def add_email(message):
        user_lang(message)
        if '/' not in message.text:
            data = select_user(db, table, message.from_user.id, '*')
            if validate_email(message.text.lower()):
                if '@kindle.com' in message.text.lower():
                    upd_user_email(db, table, message.from_user.id, '"' +
                        str(message.text) + '"')
                    # check = select_user(db, table, message.from_user.id,
                    #     'remetente')
                    if len(data[3]) < 5:
                        msg = bot.reply_to(message, i18n.t('bot.askemail'))
                        bot.register_next_step_handler(msg, add_email)
                        return 0
                    msg = bot.reply_to(message,
                        str(u'\U00002705') + i18n.t('bot.success'),
                        parse_mode='HTML', reply_markup=button)
                # elif len(data[3]) < 5:
                #     msg = bot.reply_to(message,
                #         'Type your email used on your Amazon account.')
                #     bot.register_next_step_handler(msg, add_email)
                #     return 0
                else:
                    upd_user_email(db, table, message.from_user.id, '"' +
                        str(message.text) + '"')
                    msg = bot.reply_to(message,
                        str(u'\U00002705') + i18n.t('bot.success'),
                        parse_mode='HTML', reply_markup=button)
            else:
                msg = bot.send_message(message.from_user.id, str(u'\U000026A0')
                    + i18n.t('bot.askemail'), parse_mode='HTML')
                bot.register_next_step_handler(msg, add_email)
        else:
            msg = bot.send_message(message.from_user.id,
            i18n.t('bot.askemail'), parse_mode='HTML')
        bot.register_next_step_handler(msg, add_email)

    @bot.message_handler(commands=['send'])
    def ask_file(message):
        user_lang(message)
        msg = bot.send_message(message.from_user.id,
            i18n.t('bot.askfile'))
        bot.register_next_step_handler(msg, get_file)

    def get_file(message):
        user_lang(message)
        if message.content_type == 'document':
            file_size = message.document.file_size
            bot.reply_to(message, str(u'\U00002705') + 'Downloaded '
                + str(file_size) + ' bytes.')
            file_info = bot.get_file(message.document.file_id)
            file_url = ('https://api.telegram.org/file/bot' + TOKEN + '/'
                + file_info.file_path)
            # print(file_url)
        elif message.content_type == 'text':
            if message.text.lower() in cmds:
                return 0
            file_url = message.text
        else:
            msg = bot.send_message(message.from_user.id, i18n.t('bot.askfile'))
            bot.register_next_step_handler(msg, get_file)
            return 0

        # data = select_user(db, table, message.from_user.id, '*')
        # f = requests.get(file_url)
        upd_user_file(db, table, message.from_user.id, file_url)
        # print(file_url)
        if '.pdf' in file_url.lower():
            msg = bot.send_message(message.from_user.id, i18n.t('bot.askconvert'),
                parse_mode='HTML', reply_markup=button2)
        else:
            data = select_user(db, table, message.from_user.id, '*')
            send_mail(str(message.from_user.id), data[2],
                data[3], ' ', str(message.from_user.id), data[7])

        # bot.register_next_step_handler(msg, ask_conv)

    @bot.callback_query_handler(lambda q: q.data == '/converted')
    def ask_conv(call):
        bot.answer_callback_query(call.id)
        data = select_user(db, table, call.from_user.id, '*')
        send_mail(str(call.from_user.id), data[2],
            data[3], 'Convert', str(call.from_user.id), data[7])

    @bot.callback_query_handler(lambda q: q.data == '/as_is')
    def ask_conv(call):
        bot.answer_callback_query(call.id)
        data = select_user(db, table, call.from_user.id, '*')
        send_mail(str(call.from_user.id), data[2],
            data[3], ' ', str(call.from_user.id), data[7])

    @bot.callback_query_handler(lambda q: q.data == '/email')
    def email(call):
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.from_user.id, i18n.t('bot.askemail3'))
        bot.register_next_step_handler(msg, add_email)

    @bot.callback_query_handler(lambda q: q.data == '/send')
    def ask_file(call):
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.from_user.id,
            i18n.t('bot.askfile'))
        bot.register_next_step_handler(msg, get_file)

    @bot.message_handler(func=lambda m: True)
    def generic_msg(message):
        user_lang(message)
        if '@' not in message.text:
            bot.send_chat_action(message.chat.id, 'typing')
            get_file(message)

    @bot.message_handler(content_types=['document'])
    def generic_file(message):
        user_lang(message)
        bot.send_chat_action(message.chat.id, 'typing')
        get_file(message)

    bot.polling(none_stop=True)
