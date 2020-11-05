import configparser
import datetime
import logging
import logging.handlers
import sqlite3

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.sections()
    BOT_CONFIG_FILE = "kindle.conf"
    config.read(BOT_CONFIG_FILE)
    log_file = config["DEFAULT"]["logfile"]
    db = config["SQLITE3"]["data_base"]
    table = config["SQLITE3"]["table"]

    LOG_INFO_FILE = log_file
    logger_info = logging.getLogger("InfoLogger")
    logger_info.setLevel(logging.DEBUG)
    handler_info = logging.handlers.RotatingFileHandler(
        LOG_INFO_FILE, maxBytes=10240, backupCount=5, encoding="utf-8"
    )
    logger_info.addHandler(handler_info)

    conn = sqlite3.connect(db)

    cursor = conn.cursor()

    aux = (
        """CREATE TABLE {} (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        chatid TEXT NOT NULL,
        remetente TEXT,
        destinatario TEXT,
        criacao DATE NOT NULL,
        usado DATE,
        idioma TEXT,
        arquivo TEXT);
    """
    ).format(table)

    aux2 = ('''SELECT * FROM "{}"''').format(table)

    try:
        cursor.execute(aux)
        logger_info.info(
            str(datetime.datetime.now()) + " Tabela usuarios criada"
        )
    except:
        cursor.execute(aux2)
        usuarios = cursor.fetchall()
        for user in usuarios:
            print(user)
        pass

    conn.commit()
    conn.close()
