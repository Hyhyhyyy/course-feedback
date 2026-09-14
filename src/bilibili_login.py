"""User-confirmed official QR login; session stays in this local process."""
import base64
import http.cookiejar
import io
import json
import threading
import time
import urllib.request
from urllib.parse import urlencode, urlparse


class BilibiliLogin:
    def __init__(self):
        self.lock=threading.RLock();self.jar=http.cookiejar.MozillaCookieJar()
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.key=None;self.created=0;self.last_poll=0;self.logged_in=False
        self.message='未连接本地登录会话；公开可访问素材可直接获取'
    def request(self,url):
        request=urllib.request.Request(url,headers={'User-Agent':'CourseFeedbackResearch/0.1','Referer':'https://www.bilibili.com/'})
        with self.opener.open(request,timeout=15) as response:return json.load(response)
    def status(self):return {'logged_in':self.logged_in,'message':self.message}
    def start(self):
        import qrcode
        import qrcode.image.svg
        with self.lock:
            response=self.request('https://passport.bilibili.com/x/passport-login/web/qrcode/generate')
            if response.get('code')!=0:raise ValueError('B站未能生成登录二维码')
            data=response['data'];url=data['url']
            if urlparse(url).scheme!='https' or urlparse(url).hostname not in ('passport.bilibili.com','account.bilibili.com'):raise ValueError('登录地址校验失败')
            self.key=data['qrcode_key'];self.created=time.monotonic();self.last_poll=0;self.logged_in=False
            self.message='请使用B站App扫码，并在官方界面确认登录'
            image=qrcode.make(url,image_factory=qrcode.image.svg.SvgPathFillImage)
            stream=io.BytesIO();image.save(stream)
            return {'qr_image':'data:image/svg+xml;base64,'+base64.b64encode(stream.getvalue()).decode(),
                    'login_url':url,'message':self.message}
    def poll(self):
        with self.lock:
            if self.logged_in:return self.status()
            if not self.key:return self.status()
            if time.monotonic()-self.created>180:
                self.message='二维码已过期，请重新登录';self.key=None;return self.status()
            if time.monotonic()-self.last_poll<3:return self.status()
            self.last_poll=time.monotonic()
            response=self.request('https://passport.bilibili.com/x/passport-login/web/qrcode/poll?'+urlencode({'qrcode_key':self.key}))
            if response.get('code')!=0:raise ValueError('B站登录状态查询失败')
            data=response['data']
            if data.get('code')==0:
                nav=self.request('https://api.bilibili.com/x/web-interface/nav')
                self.logged_in=nav.get('code')==0 and nav.get('data',{}).get('isLogin') is True
                self.message='B站登录已验证，本地获取任务将使用此会话' if self.logged_in else '官方登录已确认，但本地会话尚未验证成功'
                self.key=None
            else:self.message=data.get('message') or '等待扫码确认'
            return self.status()
    def export_for_job(self,path):
        with self.lock:
            if not self.logged_in:return None
            self.jar.save(str(path),ignore_discard=True,ignore_expires=False)
            return str(path)
    def clear(self):
        with self.lock:
            self.jar.clear();self.key=None;self.logged_in=False;self.message='本地登录会话已清除'
            return self.status()
