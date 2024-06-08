import json
import requests

def send_message(bot_token, destination, message, message_effect_id):
    url = 'http://localhost:8080/send_message'
    payload = {
        'bot_token': bot_token,
        'destination': destination,
        'message': message,
        'message_effect_id': message_effect_id,
    }
    response = requests.post(url, json=payload)

