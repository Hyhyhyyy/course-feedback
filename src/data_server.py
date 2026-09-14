"""Local acquisition UI with user-confirmed QR login and artifact-based results."""
import argparse
import json
import secrets
import threading
import uuid
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from acquire_course import normalize_url
from fetch_course import fetch,public_summary,save_json
from bilibili_login import BilibiliLogin


def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8766);args=p.parse_args()
    root=Path(__file__).resolve().parents[1];jobs=root/'outputs/jobs';jobs.mkdir(parents=True,exist_ok=True)
    token=secrets.token_urlsafe(32);lock=threading.Lock();workers={};login=BilibiliLogin()
    def folder(jid):
        if jid=='real-acquisition':return root/'outputs/real-acquisition'
        if len(jid)!=32 or any(c not in '0123456789abcdef' for c in jid):raise ValueError('任务编号无效')
        return jobs/jid/'assets'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,status,data,kind='application/json; charset=utf-8',attachment=False):
            body=json.dumps(data,ensure_ascii=False).encode() if isinstance(data,dict) else data
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            if attachment:self.send_header('Content-Disposition','attachment; filename="course-comments.json"')
            self.end_headers();self.wfile.write(body)
        def valid_host(self):return self.headers.get('Host') in (f'127.0.0.1:{args.port}',f'localhost:{args.port}')
        def do_GET(self):
            if not self.valid_host():return self.send(403,{'error':'仅允许本机访问'})
            parsed=urlparse(self.path);path=parsed.path
            try:
                if path=='/':return self.send(200,(root/'web/index.html').read_text(encoding='utf-8').replace('__TOKEN__',token).encode(),'text/html; charset=utf-8')
                if path=='/api/login/status':return self.send(200,login.status())
                if path=='/api/acquisition/latest':
                    candidates=[root/'outputs/real-acquisition/acquisition.json',*jobs.glob('*/assets/acquisition.json')]
                    candidates=[c for c in candidates if c.exists()]
                    latest=max(candidates,key=lambda c:c.stat().st_mtime) if candidates else None
                    jid=('real-acquisition' if latest.parent.name=='real-acquisition' else latest.parent.parent.name) if latest else None
                    return self.send(200,{'id':jid})
                if path.startswith('/api/acquisition/'):
                    parts=path.split('/');out=folder(parts[3]);record=out/'acquisition.json'
                    if not record.exists():return self.send(404,{'error':'尚无获取记录'})
                    if len(parts)==4:return self.send(200,public_summary(json.loads(record.read_text(encoding='utf-8'))))
                    if parts[4]=='download':
                        f=out/'comments.json'
                        if not f.exists():return self.send(404,{'error':'弹幕尚未取得'})
                        return self.send(200,f.read_bytes(),attachment=True)
                    if parts[4]=='comments':
                        offset=max(0,int(parse_qs(parsed.query).get('offset',['0'])[0]))
                        data=json.loads((out/'comments.json').read_text(encoding='utf-8'))['comments']
                        data=sorted(data,key=lambda c:(c['playback_ms'],c['source_row']))
                        return self.send(200,{'comments':data[offset:offset+50],'total':len(data)})
                examples={'/example':'outputs/synthetic-demo/index.html','/model-example':'outputs/model-demo/index.html',
                          '/media-example':'outputs/media-smoke/model-report/index.html'}
                if path in examples:
                    f=root/examples[path]
                    if f.exists():return self.send(200,f.read_bytes(),'text/html; charset=utf-8')
                return self.send(404,{'error':'未找到'})
            except (ValueError,KeyError,IndexError):return self.send(400,{'error':'请求参数或记录格式无效'})
            except OSError:return self.send(404,{'error':'本地素材暂不可读取'})
        def do_POST(self):
            if not self.valid_host():return self.send(403,{'error':'仅允许本机访问'})
            if self.headers.get('X-Demo-Token')!=token:return self.send(403,{'error':'会话校验失败，请刷新页面'})
            if self.headers.get('Origin') not in (None,f'http://127.0.0.1:{args.port}',f'http://localhost:{args.port}'):
                return self.send(403,{'error':'来源不允许'})
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<4096:raise ValueError('请求大小无效')
                data=json.loads(self.rfile.read(n))
                if self.path=='/api/login/start':return self.send(200,login.start())
                if self.path=='/api/login/poll':return self.send(200,login.poll())
                if self.path=='/api/login/clear':return self.send(200,login.clear())
                if self.path!='/api/acquire':return self.send(404,{'error':'未找到'})
                url=normalize_url(data['url'])
                with lock:
                    if any(t.is_alive() for t in workers.values()):return self.send(409,{'error':'已有获取任务进行中'})
                    jid=uuid.uuid4().hex;out=folder(jid);out.mkdir(parents=True)
                    save_json(out/'acquisition.json',{'status':'running','artifacts':{},'stages':[]})
                    def worker():
                        cookie=out/'.session.cookies.txt'
                        try:fetch(url,out,login.export_for_job(cookie))
                        except Exception as exc:save_json(out/'acquisition.json',{'status':'acquisition_failed','artifacts':{},'stages':[],
                            'error_type':type(exc).__name__,'error':'任务启动失败，请检查本地运行环境'})
                        finally:
                            if cookie.exists():cookie.unlink()
                    thread=threading.Thread(target=worker,daemon=True);workers[jid]=thread;thread.start()
                return self.send(202,{'id':jid})
            except (ValueError,KeyError,TypeError,AttributeError):return self.send(400,{'error':'参数无效或登录响应未通过校验'})
            except Exception as exc:return self.send(502,{'error':'官方登录服务暂未返回有效结果：'+type(exc).__name__})
    print(f'http://127.0.0.1:{args.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()


if __name__=='__main__':main()
