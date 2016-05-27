import configparser
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from email import encoders
import logging
import logging.handlers
import os
#import requests
import smtplib
import sqlite3
import sys
import telebot
from telebot import types
import urllib.request


def send_mail( send_from, send_to, subject, text, file_url, server="localhost",
    port=587, username='', password='', isTls=True):

    return 0


def add_user(db, table, chatid, destinatario):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    aux = ('''INSERT INTO {} (chatid, remetente, destinatario, criacao, usado)
        VALUES ('{}', 'remetente@gabrf.com', '{}',
        '{}', '{}')''').format(table, chatid, destinatario,
        str(datetime.datetime.now()), str(datetime.datetime.now()))
    cursor.execute(aux)
    conn.commit()
    conn.close()


def upd_user_last(db, table, chatid):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    aux = ('''UPDATE {} SET usado = {}
        WHERE chatid = {}''').format(table, str(datetime.datetime.now()))
    cursor.execute(aux)
    conn.commit()
    conn.close()


def upd_user_email(db, table, chatid, destinatario):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    aux = ('''UPDATE {} SET destinatario = {}
        WHERE chatid = {}''').format(table, destinatario, chatid)
    # print(aux)
    cursor.execute(aux)
    conn.commit()
    conn.close()


def select_user(db, table, chatid, field):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    # print(db)
    # print(table)
    aux = ('''SELECT {} FROM "{}" WHERE
        chatid="{}"''').format(field, table, str(chatid))
    # print(aux)
    cursor.execute(aux)
    usuarios = cursor.fetchone()
    # print(usuarios)
    if usuarios:
        # print('Existe')
        data = usuarios
    else:
        add_user(db, table, chatid, ' ')
        # print('Nao existe')
        data = ''
    #for usuarios in cursor.fetchall():
    #    print(str(usuarios))
    conn.close()
    # print(data)
    return data

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.sections()
    BOT_CONFIG_FILE = 'kindle.conf'
    config.read(BOT_CONFIG_FILE)
    log_file = config['DEFAULT']['logfile']
    TOKEN = config['DEFAULT']['TOKEN']
    db = config['SQLITE3']['data_base']
    table = config['SQLITE3']['table']

    bot = telebot.TeleBot(TOKEN)
    button = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('Send file', callback_data='/send')
    btn2 = types.InlineKeyboardButton('Set e-mail', callback_data='/email')
    button.row(btn1, btn2)
    LOG_INFO_FILE = log_file
    logger_info = logging.getLogger('InfoLogger')
    logger_info.setLevel(logging.DEBUG)
    handler_info = logging.handlers.RotatingFileHandler(LOG_INFO_FILE,
        maxBytes=10240, backupCount=5, encoding='utf-8')
    logger_info.addHandler(handler_info)

    # select_user(db, table, sys.argv[1])
    @bot.message_handler(commands=['start'])
    def start(message):
        data = select_user(db, table, message.from_user.id, '*')
        # bot.send_message(message.from_user.id, str(data))
        # print(data)
        # print('Data[3] ' + str(data[3]))
        # print(data[4])
        try:
            aux = data[3]
        except:
            aux = ' '
        if len(aux) < 3:
            msg = bot.send_message(message.from_user.id, 'Hi!\n' +
                'This bot sends files to your Kindle.\n' +
                'First, type your Kindle e-mail.', parse_mode = 'HTML')
            bot.register_next_step_handler(msg, add_email)
        else:
            bot.send_message(message.from_user.id,
            ('Welcome back! Your registered e-mail is {}.\n' +
            'To send a file to your Kindle, click <b>Send file</b>.\n' +
            'To change your e-mail, click <b>Set e-mail</b>.').format(data[3]),
            parse_mode = 'HTML', reply_markup=button)


    @bot.message_handler(commands=['email'])
    def ask_email(message):
        msg = bot.send_message(message.from_user.id, 'Type your Kindle e-mail.')
        bot.register_next_step_handler(msg, add_email)

    def add_email(message):
        if '/' not in message.text:
            if '@kindle.com' in message.text.lower():
                upd_user_email(db, table, message.from_user.id, '"' +
                    str(message.text) + '"')
                select_user(db, table, message.from_user.id, 'destinatario')
                bot.reply_to(message, 'Email registered.\n' +
                    'To send a file to your Kindle, click <b>Send file</b>.\n'
                    +  'To change your e-mail, click <b>Set e-mail</b>.',
                parse_mode = 'HTML', reply_markup=button)
            else:
                msg = bot.send_message(message.from_user.id, '<b>Error</b>. \n'
                + message.text + ' is not valid.\n' +
                'Type your Kindle e-mail.', parse_mode = 'HTML')
                bot.register_next_step_handler(msg, add_email)

    @bot.message_handler(commands=['send'])
    def ask_file(message):
        msg = bot.send_message(message.from_user.id,
            'Send me the file or the link to the file.')
        bot.register_next_step_handler(msg, get_file)

    def get_file(message):
        try:
            file_size = message.document.file_size
            bot.reply_to(message, 'Downloaded ' + str(file_size) + ' bytes.')
            file_info = bot.get_file(message.document.file_id)
            file_url = ('https://api.telegram.org/file/bot' + TOKEN + '/' 
                + file_info.file_path)
                # print(file_url)
        except:
            file_url = message.text
        send_mail('grfgabriel@gmail.com', 'gabrielrf_kindle@kindle.com', '', '', file_url)

    @bot.callback_query_handler(lambda q: q.data == '/email')
    def email(call):
        msg = bot.send_message(call.from_user.id, 'Type your Kindle e-mail')
        bot.register_next_step_handler(msg, add_email)

    @bot.callback_query_handler(lambda q: q.data == '/send')
    def ask_file(call):
        msg = bot.send_message(call.from_user.id,
            'Send me the file or the link to the file.')
        bot.register_next_step_handler(msg, get_file)


    bot.polling()
