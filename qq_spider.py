import glob
import json
import os
import time
from configparser import ConfigParser

import requests
from selenium import webdriver


class QZone(object):
    def __init__(self):
        chromedriver = "C:\Program Files (x86)\Google\Chrome\Application\chromedriver.exe"
        self.web = webdriver.Chrome(executable_path=chromedriver)
        self.web.get('https://user.qzone.qq.com')
        config = ConfigParser()
        config.read('qq_and_pw.ini')
        self._qq = config.get('userinfo', 'qq')
        self._password = config.get('userinfo', 'password')
        self.req_s = requests.Session()
        self.req_s.headers['user-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' \
                                           'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36'
        self.g_tk = None

    def login(self):
        self.web.switch_to.frame('login_frame')
        log = self.web.find_element_by_id("switcher_plogin")
        log.click()
        time.sleep(1)
        un = self.web.find_element_by_id('u')
        un.send_keys(self._qq)
        pw = self.web.find_element_by_id('p')
        pw.send_keys(self._password)
        btn = self.web.find_element_by_id('login_button')
        time.sleep(1)
        btn.click()
        time.sleep(2)
        self.web.get('https://user.qzone.qq.com/{0}'.format(self._qq))
        for x in self.web.get_cookies():
            self.req_s.cookies[x["name"]] = x["value"]
        self.g_tk = self._get_g_tk()
        self.web.quit()

    def _get_g_tk(self):
        p_skey = self.req_s.cookies['p_skey']
        h = 5381
        for i in p_skey:
            h += (h << 5) + ord(i)
        return h & 2147483647

    def get_friends_by_net(self):
        if not os.path.exists("./friends/"):
            os.mkdir("friends/")
        url = 'https://h5.qzone.qq.com/proxy/domain/base.qzone.qq.com/cgi-bin/right/get_entryuinlist.cgi'
        params = {
            "uin": self._qq,
            "fupdate": 1,
            "action": 1,
            "g_tk": self.g_tk,
            'offset': 0
        }
        friends_list = []
        while True:
            page = self.req_s.get(url=url, params=params)
            if '"uinlist":[]' in page.text:
                break
            with open('./friends/{0}.json'.format(params['offset']), 'w', encoding='utf-8') as f:
                file_json = self._js2dict(page.text)
                f.write(json.dumps(file_json, indent=4, ensure_ascii=False))
            friends_list.extend(file_json['data']['uinlist'])
            params['offset'] += 50
        return friends_list

    def get_friends_by_load(self):
        friends_list = []
        file_list = glob.glob('friends/*.json')
        for file_path in file_list:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_json = json.loads(f.read())
                friends_list.extend(file_json['data']['uinlist'])
        return friends_list

    def get_shuoshuo(self, load=True):
        if not os.path.exists("./shuoshuo/"):
            os.mkdir("shuoshuo/")
        if load:
            friends_list = self.get_friends_by_load()
        else:
            friends_list = self.get_friends_by_net()

        url = 'https://h5.qzone.qq.com/proxy/domain/taotao.qq.com/cgi-bin/emotion_cgi_msglist_v6'
        params = {
            "sort": 0,
            "start": 0,
            "num": 20,
            "cgi_host": "http://taotao.qq.com/cgi-bin/emotion_cgi_msglist_v6",
            "replynum": 100,
            "callback": "_preloadCallback",
            "code_version": 1,
            "inCharset": "utf-8",
            "outCharset": "utf-8",
            "notice": 0,
            "format": "jsonp",
            "need_private_comment": 1,
            "g_tk": self.g_tk,
            'uin': None,
            'pos': 0
        }
        for u in friends_list:
            params['pos'] = 0
            params['uin'] = u['data']
            print(u['data'], u['label'])
            while True:
                page = self.req_s.get(url=url, params=params)
                resp = page.text

                if '"msglist":null' in resp:
                    break
                elif '"message":"对不起,主人设置了保密,您没有权限查看"' in resp:
                    print('没有权限：', u['label'])
                    break

                file_name = './shuoshuo/{0}/{1}_{2}.json'.format(u['label'], u['data'], params['pos'])
                if not os.path.exists("./shuoshuo/" + u['label']):
                    os.mkdir("./shuoshuo/" + u['label'])
                with open(file_name, 'w', encoding='utf-8') as f:
                    file_json = self._js2dict(resp)
                    f.write(json.dumps(file_json, indent=4, ensure_ascii=False))
                params['pos'] += 20

    @staticmethod
    def _js2dict(js_str: str):
        return json.loads(js_str[js_str.find('(') + 1: js_str.rfind(')')])

    def run(self):
        self.login()
        self.get_shuoshuo()


if __name__ == '__main__':
    sp = QZone()
    sp.run()
