# -*- coding: utf-8 -*-
import requests
import time
import socket
import xml.etree.ElementTree as ET
import os
import shutil
import logging
import datetime
import sys
import traceback
from db_proto import Cash

INTERVAL = 0.5


def get_exception():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    return ''.join('!! ' + line for line in lines)


def human_time(timestamp):
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

class Telegram_Listener:
    def __init__(self):
        if not os.path.exists("posts"):
            os.makedirs("posts")
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
        logging.basicConfig(filename='channel.log', format='%(asctime)s %(levelname)s %(message)s', level=logging.ERROR)
        self.logger = logging.getLogger('channel.log')
        self.logger.setLevel(logging.ERROR)

        if self.proxy:
            self.proxies = get_proxies(self.cfgtree)
            self.log_event("Init completed with proxy, host: " + str(self.host))
        else:
            self.log_event("Init completed, host: " + str(self.host))

    def log_event(self, text):
        log_text = '%s >> %s' % (time.ctime(), text)
        print log_text
        self.logger.error(text)
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
            self.log_event("REAL ERROR: "+request.text)
            return False
        else:
            self.log_event("SEND_MESSAGE, text={0}".format(text))
            return True

    def get_updates(self):
        data = {'offset': self.offset + 1, 'limit': 5, 'timeout': 0}
        if self.proxy:
            request = requests.post(self.URL + self.TOKEN + '/getUpdates', data=data, proxies=self.proxies)
        else:
            request = requests.post(self.URL + self.TOKEN + '/getUpdates', data=data)
        updates_list = []

        if (not request.status_code == 200) or (not request.json()['ok']):
            return updates_list

        if not request.json()['result']:
            return updates_list
        else:
            for update in request.json()['result']:
                try:
                    telegram_update = TelegramUpdate(update, self)
                    self.offset = telegram_update.update_id
                    if telegram_update.type == 0:
                        self.log_event("GET ERROR UPDATE:")
                        self.log_event(request.json())
                    else:
                        updates_list.append(telegram_update)
                except:
                    self.log_event(update)
        return updates_list

    def get_file(self, file_link):
        self.log_event('Getting file {0}'.format(file_link))  # Logging
        data = {'file_id': file_link}  # Request create
        if self.proxy:
            request = requests.post(self.URL + self.TOKEN + '/getFile', data=data,
                                    proxies=self.proxies)  # HTTP request with proxy
        else:
            request = requests.post(self.URL + self.TOKEN + '/getFile', data=data)  # HTTP request

        file_path = request.json()['result']['file_path']
        download_url = 'https://api.telegram.org/file/bot{0}/{1}'.format(self.TOKEN, file_path)
        print download_url
        file_name = file_path.split('/')[-1]
        if self.proxy:
            request = requests.get(download_url, stream=True, proxies=self.proxies)  # HTTP request with proxy
        else:
            request = requests.get(download_url, stream=True)  # HTTP request
        with open("documents//" + file_name, 'wb') as f:
            shutil.copyfileobj(request.raw, f)
        self.log_event("File {0} getting".format(file_name))
        return "documents//" + file_name


class TelegramUpdate:
    def __init__(self, update, telebot):
        self.update_id = update["update_id"]
        self.type = 0
        if "message" in update:
            if 'text' in update['message']:
                self.type = 1
                self.text = update['message']['text'].encode("utf-8")
                self.from_id = update['message']['from']['id']
                return

            elif "photo" in update['message']:
                self.type = 4
                size = 0
                for photo in update['message']['photo']:
                    if photo["file_size"] > size:
                        file_id = photo['file_id']
                self.from_id = update['message']['chat']['id']  # Chat ID
                self.file_name = telebot.get_file(file_id)

            else:
                return

        elif "callback_query" in update:
            self.type = 2
            self.callback_text = update['callback_query']['data']
            self.callback_message_id = update['callback_query']['message']['message_id']
            self.callback_message_text = update['callback_query']['message']['text'].encode("utf-8")
            self.from_id = update['callback_query']['from']['id']
            return
        else:
            telebot.log_event("GET STRANGE UPDATE: {0}".format(update))
            return

    def __str__(self):
        if self.type == 1:
            return "[mes] (id{0}) send message: {1}".format(self.from_id, self.text)

        elif self.type == 2:
            return "[callback] (id{0}) callback: text={1}, message_id ={2} ".format(self.from_id, self.callback_text, self.callback_message_id)

        elif self.type == 4:
            return "[photo] (id{0}) photo: {1} ".format(self.from_id, self.file_name)

        else:
            return "UNKNOWN MESSAGE TYPE"


if __name__ == "__main__":
    telebot = Telegram_Listener()
    post_text = ''
    post_photo = ''
    while True:
        try:
            message_list = telebot.get_updates()
            if message_list:
                for message in message_list:
                    if message.from_id != telebot.admin_id:
                        telebot.log_event("WRONG ID: " + message)
                        continue
                    if message.type == 1:
                        if message.text == '1':
                            telebot.cash.add_post(post_text, post_photo)
                            telebot.send_message(message.from_id, "Пост добавлен")
                            post_text = ''
                            post_photo = ''
                        else:
                            post_text = message.text
                    elif message.type == 4:
                        post_photo = message.file_name
                    else:
                        telebot.log_event("SOME SHIT: " + message)
            else:
                pass
            time.sleep(telebot.interval)
        except Exception as e:
            telebot.log_event("REAL ERROR: " + get_exception())
