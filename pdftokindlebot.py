import configparser
import datetime
import logging
import logging.handlers
import sqlite3
import sys

def add_user(db, table, chatid, destinatario):
        aux = ('''INSERT INTO {} (chatid, remetente, destinatario, criacao, usado)
        VALUES ('9083328', 'remetente@gabrf.com', '{}',
        '{}', '{}')''').format(table, destinatario,
        str(datetime.datetime.now()), str(datetime.datetime.now()))

def check_user(db, table, chatid):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM ' + table + 
       ' WHERE chatid="' + str(chatid) + '"')
    usuarios = cursor.fetchall()
    if usuarios:
        print('Existe')
    else:
        print('Nao existe')
    #for usuarios in cursor.fetchall():
    #    print(str(usuarios))
    conn.close()

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.sections()
    BOT_CONFIG_FILE = 'kindle.conf'
    config.read(BOT_CONFIG_FILE)
    log_file = config['DEFAULT']['logfile']
    db = config['SQLITE3']['data_base']
    table = config['SQLITE3']['table']

    LOG_INFO_FILE = log_file
    logger_info = logging.getLogger('InfoLogger')
    logger_info.setLevel(logging.DEBUG)
    handler_info = logging.handlers.RotatingFileHandler(LOG_INFO_FILE, 
        maxBytes=10240, backupCount=5, encoding='utf-8')
    logger_info.addHandler(handler_info)

    check_user(db, table, sys.argv[1])

