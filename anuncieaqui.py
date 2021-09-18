import json
import requests

def send_message(bot_token, destination, message):
    url = 'http://localhost:8080/send_message'
    payload = {
        'bot_token': bot_token,
        'destination': destination,
        'message': message,
    }
    response = requests.post(url, json=payload)

