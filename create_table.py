import sqlite3

conn = sqlite3.connect('kindle.db')

cursor = conn.cursor()

cursor.execute('''
CREATE TABLE usuarios (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    chatid TEXT NOT NULL,
    remetente TEXT,
    destinatario TEXT,
    criacao DATE NOT NULL,
    usado DATE);
''')

conn.close()
