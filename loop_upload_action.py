import configparser
import telebot
import time
import subprocess
import sys

config = configparser.ConfigParser()
config.sections()
BOT_CONFIG_FILE = "kindle.conf"
config.read(BOT_CONFIG_FILE)
TOKEN = config["DEFAULT"]["TOKEN"]

bot = telebot.TeleBot(TOKEN)

for x in range(0,50):
    try:
        bot.send_chat_action(sys.argv[1], "upload_document")
        time.sleep(5)
    except:
        pass
