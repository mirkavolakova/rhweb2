#!/bin/usr/env python
from __future__ import absolute_import, unicode_literals, print_function

import multiprocessing
import time
import os
from sys import argv

from codecs import open

import json
import requests

#from flask import Flask
#import app
#app_dir = os.path.dirname(os.path.abspath(__file__))
#app = Flask('rhforum', template_folder=app_dir+"/templates")
#app.config.from_pyfile(app_dir+"/config.py") # XXX
import config

def telegram_post(method, **params):
    for i in range(3):
        try:
            return requests.post("https://api.telegram.org/bot{}/{}".format(config.TELEGRAM_TOKEN, method), data=params).json()
        except Exception as ex:
            print("Failed to post to Telegram: {}: {}".format(type(ex), ex))
            time.sleep(1)

def report_telegram(message):
    telegram_post("sendMessage", chat_id=config.TELEGRAM_CHAT_ID, text=message,
        parse_mode="Markdown", disable_web_page_preview=True)

def report_irc(message):
    f = open(config.IRC_IN, 'w', encoding='utf-8')
    message = message.decode('utf-8') + u"\n"
    f.write(message)

def report_mattermost(message):
    payload = {
        'text': message,
        'channel': 'test-sanky',
        'username': 'rhbot',
        'icon_url': "https://mattermost.test.retroherna.cz/api/v3/users/68qfcbhggt8ympgfhtayr3pjrw/image"
    }
    r = requests.post(config.MATTERMOST_URL, data={'payload': json.dumps(payload)})
    print(r)

def report_discord(message):
    payload = {
        'content': message,
    }
    r = requests.post(config.DISCORD_URL,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload))
    print(r, r.text)


if __name__ == '__main__':
    method = argv[1]
    message = argv[2]

    func = {"irc": report_irc,
        "telegram": report_telegram,
        "mattermost": report_mattermost,
        "discord": report_discord}[method]
    
    func_ = lambda: func(message)

    p = multiprocessing.Process(target=func_)
    p.start()

    p.join(10)

    if p.is_alive():
        print("timeout")
        p.terminate()
        p.join()
        exit(1)

print("sent?")
