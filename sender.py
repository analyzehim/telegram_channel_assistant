# -*- coding: utf-8 -*-
import requests
import time
import socket
import xml.etree.ElementTree as ET
import os
import traceback
import sys
import logging
import datetime

from db_proto import Cash

INTERVAL = 60*60



def get_exception():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    return ''.join('!! ' + line for line in lines)


def trasform_to_human_time(timestamp):
    return datetime.datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')


def get_token(tree):
    root = tree.getroot()
    token = root.findall('telegram_token')[0].text
    return token


def get_admin(tree):
    root = tree.getroot()
    admin_id = root.findall('telegram_admin_id')[0].text
    return int(admin_id)


def get_channel_id(tree):
    root = tree.getroot()
    channel_id = root.findall('channel_id')[0].text
    return channel_id


def get_proxies(tree):
    root = tree.getroot()
    proxy_url = root.findall('proxy')[0].text
    proxies = {
        "http": proxy_url,
        "https": proxy_url,
    }
    return proxies


def check_mode(tree):
    import requests

    try:
        requests.get('https://www.google.com')
        return False
    except:
        proxies = get_proxies(tree)
        requests.get('https://www.google.com', proxies=proxies)
        return True


class Telegram_Sender:
    def __init__(self):
        self.cfgtree = ET.parse('private_config.xml')
        self.proxy = check_mode(self.cfgtree)
        self.TOKEN = get_token(self.cfgtree)
        self.URL = 'https://api.telegram.org/bot'
        self.admin_id = get_admin(self.cfgtree)
        self.offset = 0
        self.cash = Cash()
        self.host = socket.getfqdn()
        self.interval = INTERVAL
        self.channel_id = get_channel_id(self.cfgtree)
        #
        # Logging
        #
        logging.basicConfig(filename='vk_sample.log', format='%(asctime)s %(levelname)s %(message)s', level=logging.ERROR)
        self.logger = logging.getLogger('vk_sample.log')
        self.logger.setLevel(logging.ERROR)

        if self.proxy:
            self.proxies = get_proxies(self.cfgtree)
            self.log_event("Init completed with proxy, host: " + str(self.host))
        else:
            self.log_event("Init completed, host: " + str(self.host))

    def log_event(self, text):
        log_text = '[SEND] %s >> %s' % (time.ctime(), text)
        print log_text
        self.logger.debug(text)
        return True

    def send_message(self, user_id, text):
        data = {'chat_id': user_id,
                'text': text,
                'parse_mode': 'HTML'}

        if self.proxy:
            request = requests.post(self.URL + self.TOKEN + '/sendMessage', data=data,
                                    proxies=self.proxies)  # HTTP request with proxy
        else:
            request = requests.post(self.URL + self.TOKEN + '/sendMessage', data=data)  # HTTP request
        if not request.status_code == 200:  # Check server status
            self.log_event("REAL ERROR: " + request.text)
            return False
        else:
            self.log_event("SEND_MESSAGE, text={0}".format(text))
            return True

    def post(self, text):
        data = {'chat_id': self.channel_id,
                'text': text,
                'parse_mode': 'HTML'}

        if self.proxy:
            request = requests.post(self.URL + self.TOKEN + '/sendMessage', data=data,
                                    proxies=self.proxies)  # HTTP request with proxy
        else:
            request = requests.post(self.URL + self.TOKEN + '/sendMessage', data=data)  # HTTP request
        if not request.status_code == 200:  # Check server status
            self.log_event("REAL ERROR: " + request.text)
            return False
        else:
            self.log_event("POST_TO_CHANNEL, TEXT:{0}".format(text))
            return True

    def post_photo(self, text, image_path):
        files = {'photo': (image_path, open(image_path, "rb"))}
        data = {"chat_id": self.channel_id,
                "parse_mode": "HTML",
                "caption": text}
        if self.proxy:
            request = requests.post(self.URL + self.TOKEN + '/sendPhoto', data=data, files=files,
                                    proxies=self.proxies)  # HTTP request with proxy
        else:
            request = requests.post(self.URL + self.TOKEN + '/sendPhoto', data=data, files=files)  # HTTP request
        if not request.status_code == 200:  # Check server status
            self.log_event("REAL ERROR: " + request.text)
            return False
        else:
            self.log_event("POST_PHOTO, TEXT:{0}, IMAGE:{1}".format(text.encode("utf-8"), image_path))
            return True


if __name__ == "__main__":
    telebot = Telegram_Sender()
    allow_hours = [12, 18]
    #allow_hours = range(0, 24)
    while True:
        if datetime.datetime.now().hour in allow_hours:
            telebot.log_event("RIGHT TIME!")
            post = telebot.cash.get_post()
            if post:
                try:
                    if "photo" in post:
                        telebot.post_photo(post["text"], post["photo"])
                    else:
                        telebot.post(post["text"])
                except:
                    telebot.log_event(get_exception())
                telebot.cash.delete_post(post["id"])
                telebot.log_event("SLEEP!")
                time.sleep(telebot.interval)
                telebot.log_event("AWAKE!")
