import configparser
import datetime
import logging
import logging.handlers
import sqlite3

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.sections()
    BOT_CONFIG_FILE = 'kindle.conf'
    config.read(BOT_CONFIG_FILE)
    log_file = config['DEFAULT']['logfile']
    db = config['SQLITE3']['data_base']

    LOG_INFO_FILE = log_file
    logger_info = logging.getLogger('InfoLogger')
    logger_info.setLevel(logging.DEBUG)
    handler_info = logging.handlers.RotatingFileHandler(LOG_INFO_FILE,maxBytes=10240,backupCount=5,encoding='utf-8')
    logger_info.addHandler(handler_info)

    conn = sqlite3.connect(db)
    conn.close()

    logger_info.info(str(datetime.datetime.now()) + ' Banco de dados criado')
