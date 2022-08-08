import configparser
import pika
import json
import telebot
import sqlite3

rabbitmq_con = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
rabbit = rabbitmq_con.channel()

def send_file(rbt, method, properties, data):
    data=data
    rbt.basic_ack(delivery_tag=method.delivery_tag)
    data = json.loads(data)
    print(data)

rabbit.basic_qos(prefetch_count=1)
rabbit.basic_consume(queue='Send2KindleBot', on_message_callback=send_file)
rabbit.start_consuming()
