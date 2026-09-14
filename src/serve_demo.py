"""Loopback-only launcher. Keeps credentials and acquisition settings on the host."""
import argparse
import json
import os
import secrets
import subprocess
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from acquire_course import normalize_url


PAGE='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>课程反馈 · 开始分析</title><style>body{background:#f2f6f7;color:#173643;font:16px/1.8 "Microsoft YaHei",sans-serif;max-width:850px;margin:70px auto;padding:24px}h1{font-size:30px}section{padding:28px;background:white;border:1px solid #d8e4e8;border-radius:14px;margin:20px 0}input{box-sizing:border-box;width:100%;padding:14px;border:1px solid #bdd0d6;border-radius:7px;font-size:16px}button,a.button{display:inline-block;font:inherit;padding:10px 20px;margin:14px 10px 0 0;border:0;border-radius:7px;background:#245f70;color:white;cursor:pointer;text-decoration:none}.muted{color:#667f8a;font-size:14px}pre{white-space:pre-wrap;overflow-wrap:anywhere}#error{color:#a44136}</style><h1>把一节课的反馈，整理成可复盘的依据</h1><p>输入课程链接，交给后台按阶段获取、转写和分析。</p><section><label for="url">B站课程链接</label><input id="url" placeholder="https://www.bilibili.com/video/BV..."><button id="login">打开课程并登录B站</button><button id="start">开始分析</button><p class="muted">登录在B站官方页面完成。本地下载会话需单独配置；当前尚未实现网页登录后的自动同步。素材获取失败会停止任务。</p><p id="setup"></p><p id="error" role="alert"></p></section><section><h2>任务进度</h2><pre id="progress">尚未开始</pre><a id="result" class="button" hidden>打开报告</a></section><a href="/example">查看规则基线功能演示</a> · <a href="/media-example">查看音视频与模型联合试跑（语义检查未通过）</a><script>const token='__TOKEN__';const $=id=>document.getElementById(id);fetch('/api/status').then(r=>r.json()).then(s=>{$('setup').textContent=s.message});$('login').onclick=()=>{try{const u=new URL($('url').value);if(u.protocol!=='https:'||!['www.bilibili.com','bilibili.com'].includes(u.hostname))throw Error();window.open(u.href,'_blank','noopener,noreferrer')}catch{$('error').textContent='请填写有效的B站完整视频链接'}};$('start').onclick=async()=>{$('error').textContent='';$('result').hidden=true;const r=await fetch('/api/start',{method:'POST',headers:{'Content-Type':'application/json','X-Demo-Token':token},body:JSON.stringify({url:$('url').value})});const d=await r.json();if(!r.ok){$('error').textContent=d.error;return}poll(d.id)};async function poll(id){const r=await fetch('/api/job/'+id);const d=await r.json();$('progress').textContent=JSON.stringify(d,null,2);if(d.report_ready){$('result').href='/reports/'+id;$('result').hidden=false}if(d.status==='running')setTimeout(()=>poll(id),2000)}</script></html>'''


def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8766);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];jobs=root/'outputs/jobs';jobs.mkdir(parents=True,exist_ok=True)
    token=secrets.token_urlsafe(32);active={};lock=threading.Lock()
    def readiness():
        missing=[]
        if not os.environ.get('COURSE_ACCESS_RECORD') or not Path(os.environ['COURSE_ACCESS_RECORD']).is_file():missing.append('素材取得与处理记录')
        if not os.environ.get('COURSE_MODEL_URL') or not os.environ.get('COURSE_MODEL_NAME'):missing.append('模型服务地址及模型名')
        return missing
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,status,body,kind='application/json; charset=utf-8'):
            data=json.dumps(body,ensure_ascii=False).encode() if isinstance(body,dict) else body
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
        def do_GET(self):
            if self.headers.get('Host') not in (f'127.0.0.1:{a.port}',f'localhost:{a.port}'):return self.send(403,{'error':'仅允许本机访问'})
            path=urlparse(self.path).path
            if path=='/':return self.send(200,PAGE.replace('__TOKEN__',token).encode(),'text/html; charset=utf-8')
            if path=='/api/status':
                missing=readiness();return self.send(200,{'ready':not missing,'message':'待配置：'+'、'.join(missing) if missing else '基础配置已填写，服务与素材访问在实际任务中验证。'})
            if path in ('/example','/model-example','/media-example'):
                relative={'/example':'outputs/synthetic-demo/index.html','/model-example':'outputs/model-demo/index.html',
                          '/media-example':'outputs/media-smoke/model-report/index.html'}[path]
                f=root/relative
                return self.send(200,f.read_bytes(),'text/html; charset=utf-8') if f.exists() else self.send(404,{'error':'先运行合成数据演示'})
            if path.startswith('/api/job/') or path.startswith('/reports/'):
                jid=path.rsplit('/',1)[-1]
                if len(jid)!=32 or any(c not in '0123456789abcdef' for c in jid):return self.send(400,{'error':'任务编号无效'})
                report=jobs/jid/'report/index.html';status=jobs/jid/'job.json'
                if path.startswith('/reports/'):
                    return self.send(200,report.read_bytes(),'text/html; charset=utf-8') if report.exists() else self.send(404,{'error':'报告尚未生成'})
                if not status.exists():return self.send(404,{'error':'任务不存在'})
                try:data=json.loads(status.read_text(encoding='utf-8'))
                except json.JSONDecodeError:return self.send(200,{'status':'running','message':'正在更新任务状态'})
                # Do not expose local paths or subprocess errors to the browser.
                return self.send(200,{'status':data['status'],'stages':data.get('stages',[]),
                                      'report_ready':data['status']=='demo_completed' and report.exists(),
                                      'error':data.get('error_type')})
            return self.send(404,{'error':'未找到'})
        def do_POST(self):
            if self.headers.get('Host') not in (f'127.0.0.1:{a.port}',f'localhost:{a.port}'):return self.send(403,{'error':'仅允许本机访问'})
            if self.path!='/api/start':return self.send(404,{'error':'未找到'})
            if self.headers.get('X-Demo-Token')!=token:return self.send(403,{'error':'会话校验失败，请重新打开首页'})
            if self.headers.get('Origin') not in (None,f'http://127.0.0.1:{a.port}',f'http://localhost:{a.port}'):return self.send(403,{'error':'来源不允许'})
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<4096:raise ValueError('请求大小不合法')
                data=json.loads(self.rfile.read(n));url=normalize_url(data['url'])
                missing=readiness()
                if missing:raise ValueError('待配置：'+'、'.join(missing))
                with lock:
                    if any(proc.poll() is None for proc in active.values()):raise ValueError('已有任务运行中，请等待完成')
                    jid=uuid.uuid4().hex;out=jobs/jid;out.mkdir()
                    (out/'job.json').write_text(json.dumps({'status':'running','stages':[]}),encoding='utf-8')
                    cmd=[sys.executable,str(root/'src/oneclick.py'),'--url',url,'--out',str(out),
                         '--access-record',os.environ['COURSE_ACCESS_RECORD'],'--model-url',os.environ['COURSE_MODEL_URL'],
                         '--model',os.environ['COURSE_MODEL_NAME'],'--asr-model',os.environ.get('COURSE_ASR_MODEL','small')]
                    if os.environ.get('COURSE_COOKIE_FILE'):cmd+=['--cookie-file',os.environ['COURSE_COOKIE_FILE']]
                    with (out/'process.log').open('w',encoding='utf-8') as log:
                        active[jid]=subprocess.Popen(cmd,stdout=log,stderr=log,cwd=root)
                    def watch(proc,folder):
                        code=proc.wait()
                        state_path=folder/'job.json'
                        try:state=json.loads(state_path.read_text(encoding='utf-8'))
                        except (OSError,json.JSONDecodeError):state={'status':'running','stages':[]}
                        if state['status']=='running':
                            state.update(status='failed',error_type='WorkerExit',exit_code=code)
                            state_path.write_text(json.dumps(state),encoding='utf-8')
                    threading.Thread(target=watch,args=(active[jid],out),daemon=True).start()
                return self.send(202,{'id':jid})
            except (ValueError,KeyError) as exc:return self.send(400,{'error':str(exc)})
    print(f'http://127.0.0.1:{a.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()


if __name__=='__main__':main()
