import sqlite3


class Cash:
    def __init__(self):
        self.con = sqlite3.connect('cash.db')
        self.cur = self.con.cursor()
        self.cur.execute('''CREATE TABLE IF NOT EXISTS `Posts_Contents`
                    ("id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL ,
                     "text" VARCHAR(1000),
                     "imagePath" VARCHAR(1000));
                    ''')

    def add_post(self, text, image_path):
        self.cur.execute('''INSERT OR REPLACE INTO Posts_Contents(text, imagePath) VALUES ('{0}','{1}')'''.format(text, image_path))
        self.con.commit()
        return True

    def get_all_posts(self):
        self.cur.execute('SELECT * FROM Posts_Contents')
        posts_texts = self.cur.fetchall()
        return posts_texts

    def delete_post(self, post_id):
        self.cur.execute('''DELETE FROM Posts_Contents WHERE id="{0}"'''.format(post_id))
        self.con.commit()
        return True

    def get_post(self):
        self.cur.execute('''SELECT * FROM Posts_Contents WHERE id =(SELECT MIN(ID) FROM Posts_Contents)''')
        resp = self.cur.fetchone()
        post = {}
        if resp:
            post["id"] = int(resp[0])
            post["text"] = resp[1]
            if resp[2]:
                post["photo"] = resp[2]
        return post
