import configparser
import sqlite3

config = configparser.ConfigParser()
config.sections()
BOT_CONFIG_FILE = "kindle.conf"
config.read(BOT_CONFIG_FILE)
db = config["SQLITE3"]["data_base"]

def check_premium_user(userid):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    aux = (f'SELECT saldo FROM "premium" WHERE chatid = {userid}')
    cursor.execute(aux)
    result = cursor.fetchone()
    conn.commit()
    conn.close()
    return result

def add_premium_user(userid, quantity):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    aux = (f'INSERT INTO "premium" (chatid, saldo) VALUES ({userid}, {quantity})')
    cursor.execute(aux)
    conn.commit()
    conn.close()

def update_saldo_premium(userid, saldo):
    print(f'Atualizando {userid} com saldo {saldo}')
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    aux = (f'UPDATE "premium" SET saldo = {saldo} WHERE chatid = {userid}')
    cursor.execute(aux)
    conn.commit()
    conn.close()

def delete_premium_user(userid):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    aux = (f'DELETE FROM "premium" WHERE chatid = {userid}')
    cursor.execute(aux)
    conn.commit()
    conn.close()

def get_premium_users(value):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    aux = (f'SELECT * FROM "premium" WHERE CAST(saldo as INTEGER) > {value} ORDER BY CAST(saldo as INTEGER) DESC')
    cursor.execute(aux)
    result = cursor.fetchall()
    conn.commit()
    conn.close()
    return result
