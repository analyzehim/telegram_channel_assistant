import sqlite3
import logging
import time

class Cash:
    def __init__(self):
        self.con = sqlite3.connect('cash.db')
        self.cur = self.con.cursor()
        logging.basicConfig(filename='channel.log', format='%(asctime)s %(levelname)s %(message)s',
                            level=logging.ERROR)
        self.logger = logging.getLogger('channel.log')
        self.logger.setLevel(logging.ERROR)
        self.cur.execute('''CREATE TABLE IF NOT EXISTS `Posts_Contents`
                    ("id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL ,
                     "text" VARCHAR(1000),
                     "imagePath" VARCHAR(1000));
                    ''')

    def log_event(self, text):
        log_text = '[DB] %s >> %s' % (time.ctime(), text)
        print log_text
        self.logger.error(text)
        return True

    def add_post(self, text, image_path):
        self.cur.execute('''INSERT OR REPLACE INTO Posts_Contents(text, imagePath) VALUES ('{0}','{1}')'''.format(text, image_path))
        self.con.commit()
        if image_path:
            self.log_event("ADD POST: text: {0}, image_path: {1}".format(text, image_path))
        else:
            self.log_event("ADD POST: text: {0}, no image".format(text, image_path))
        return True

    def delete_post(self, post_id):
        self.cur.execute('''DELETE FROM Posts_Contents WHERE id="{0}"'''.format(post_id))
        self.con.commit()
        self.log_event("DELETE POST ID{0}".format(post_id))
        return True

    def get_post(self):
        self.cur.execute('''SELECT * FROM Posts_Contents WHERE id =(SELECT MIN(ID) FROM Posts_Contents)''')
        resp = self.cur.fetchone()
        post = {}
        if resp:
            post["id"] = int(resp[0])
            post["text"] = resp[1].encode('utf-8')
            if resp[2]:
                post["photo"] = resp[2]
            self.log_event("RETURN POST: {0}".format(post))
        return post
