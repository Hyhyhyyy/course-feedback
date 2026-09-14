"""User-confirmed official QR login; session stays in this local process."""
import base64
import http.cookiejar
import io
import json
import threading
import time
import datetime
import urllib.request
from urllib.parse import urlencode, urlparse


class BilibiliLogin:
    def __init__(self):
        self.lock=threading.RLock();self.jar=http.cookiejar.MozillaCookieJar()
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.key=None;self.created=0;self.last_poll=0;self.logged_in=False
        self.state='disconnected';self.profile=None;self.checked_at=None;self.last_check=0
        self.message='未连接本地登录会话；公开可访问素材可直接获取'
    def request(self,url):
        request=urllib.request.Request(url,headers={'User-Agent':'CourseFeedbackResearch/0.1','Referer':'https://www.bilibili.com/'})
        with self.opener.open(request,timeout=15) as response:return json.load(response)
    def status(self):
        with self.lock:
            if self.key and time.monotonic()-self.created>180:
                self.key=None;self.state='qr_expired';self.message='二维码已过期，请重新生成'
            remaining=max(0,int(180-(time.monotonic()-self.created))) if self.key else 0
            return {'logged_in':self.logged_in,'message':self.message,'state':self.state,
                    'profile':self.profile if self.logged_in else None,'checked_at':self.checked_at,
                    'verification_stale':bool(self.logged_in and time.monotonic()-self.last_check>300),
                    'qr_remaining_seconds':remaining,'session_scope':'仅当前本机服务进程，重启后需重新登录'}
    def accept_nav(self,nav):
        self.last_check=time.monotonic();self.checked_at=datetime.datetime.now().astimezone().isoformat()
        data=nav.get('data',{})
        if nav.get('code')==0 and data.get('isLogin') is True:
            self.logged_in=True;self.state='connected'
            self.profile={'name':str(data.get('uname') or '已验证账号'),'uid':str(data.get('mid') or ''),
                          'level':data.get('level_info',{}).get('current_level')}
            self.message='B站登录已验证，获取任务将使用此本地会话'
        else:
            self.logged_in=False;self.profile=None
            if nav.get('code') in (0,-101):
                self.state='expired';self.message='本地会话未登录或已失效，请扫码连接'
            else:self.state='verification_failed';self.message='官方未返回有效验证结果，请稍后检查连接'
        return self.status()
    def refresh(self):
        with self.lock:
            if time.monotonic()-self.last_check<5:return self.status()
            try:return self.accept_nav(self.request('https://api.bilibili.com/x/web-interface/nav'))
            except Exception:
                self.logged_in=False;self.profile=None;self.state='verification_failed'
                self.message='暂时无法连接官方验证服务，请稍后重试';self.last_check=time.monotonic()
                return self.status()
    def start(self):
        import qrcode
        import qrcode.image.svg
        with self.lock:
            response=self.request('https://passport.bilibili.com/x/passport-login/web/qrcode/generate')
            if response.get('code')!=0:raise ValueError('B站未能生成登录二维码')
            data=response['data'];url=data['url']
            if urlparse(url).scheme!='https' or urlparse(url).hostname not in ('passport.bilibili.com','account.bilibili.com'):raise ValueError('登录地址校验失败')
            self.key=data['qrcode_key'];self.created=time.monotonic();self.last_poll=0;self.logged_in=False
            self.profile=None;self.state='waiting_scan'
            self.message='请使用B站App扫码，并在官方界面确认登录'
            image=qrcode.make(url,image_factory=qrcode.image.svg.SvgPathFillImage)
            stream=io.BytesIO();image.save(stream)
            return {**self.status(),'qr_image':'data:image/svg+xml;base64,'+base64.b64encode(stream.getvalue()).decode(),
                    'login_url':url}
    def poll(self):
        with self.lock:
            if self.logged_in:return self.status()
            if not self.key:return self.status()
            if time.monotonic()-self.created>180:
                self.message='二维码已过期，请重新登录';self.state='qr_expired';self.key=None;return self.status()
            if time.monotonic()-self.last_poll<3:return self.status()
            self.last_poll=time.monotonic()
            response=self.request('https://passport.bilibili.com/x/passport-login/web/qrcode/poll?'+urlencode({'qrcode_key':self.key}))
            if response.get('code')!=0:raise ValueError('B站登录状态查询失败')
            data=response['data']
            if data.get('code')==0:
                nav=self.request('https://api.bilibili.com/x/web-interface/nav')
                self.accept_nav(nav)
                self.key=None
            else:
                self.state={86101:'waiting_scan',86090:'waiting_confirm',86038:'qr_expired'}.get(data.get('code'),'verification_failed')
                self.message=data.get('message') or '等待扫码确认'
                if self.state=='qr_expired':self.key=None
            return self.status()
    def export_for_job(self,path):
        with self.lock:
            if self.logged_in and time.monotonic()-self.last_check>300:self.refresh()
            if not self.logged_in:return None
            self.jar.save(str(path),ignore_discard=True,ignore_expires=False)
            return str(path)
    def clear(self):
        with self.lock:
            self.jar.clear();self.key=None;self.logged_in=False;self.profile=None;self.state='disconnected'
            self.checked_at=None;self.last_check=0;self.message='本地登录会话已清除'
            return self.status()
