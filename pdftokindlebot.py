import configparser
import datetime
import logging
import logging.handlers
import telebot
import sqlite3
import sys

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
    if usuarios:
        # print('Existe')
        data = usuarios
    else:
        add_user(db, table, chatid, 'None')
        # print('Nao existe')
        data = 'None'
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
        bot.send_message(message.from_user.id, str(data))
        print(data[3])
        if data[3] == 'None':
            msg = bot.send_message(message.from_user.id, 'Type your Kindle e-mail.')
            bot.register_next_step_handler(msg, ask_email)
            

    @bot.message_handler(commands=['email'])
    def ask_email(message): 
        msg = bot.send_message(message.from_user.id, 'Type your Kindle e-mail.')
        bot.register_next_step_handler(msg, add_email)

    def add_email(message):
        upd_user_email(db, table, message.from_user.id, '"' + str(message.text) + '"') 
        select_user(db, table, message.from_user.id, 'destinatario')
        bot.reply_to(message, 'Email registered.')

    bot.polling()
