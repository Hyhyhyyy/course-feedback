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
from workbench import run_analysis,analysis_dir,analysis_status,read_json
from course_feedback.pipeline import read_transcript
from syllabus import parse_upload,present_report


def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8766);args=p.parse_args()
    root=Path(__file__).resolve().parents[1];jobs=root/'outputs/jobs';jobs.mkdir(parents=True,exist_ok=True)
    token=secrets.token_urlsafe(32);lock=threading.Lock();workers={};analysis_workers={};login=BilibiliLogin()
    for stale in [*jobs.glob('*/analysis/state.json'),root/'outputs/real-acquisition/analysis/state.json']:
        state=read_json(stale,{})
        if state.get('status')=='running':
            state.update(status='interrupted',stage='服务重启，任务已中断；可以重试');save_json(stale,state)
    def folder(jid):
        if jid=='real-acquisition':return root/'outputs/real-acquisition'
        if len(jid)!=32 or any(c not in '0123456789abcdef' for c in jid):raise ValueError('任务编号无效')
        return jobs/jid/'assets'
    def saved_report(assets):
        out=analysis_dir(assets)
        report=read_json(out/'report.json')
        if report is None:raise ValueError('尚无已生成报告')
        report=present_report(report,read_json(out/'syllabus.json'))
        attempt=analysis_status(assets)
        report['last_attempt_status']=attempt.get('status')
        report['report_notice']='' if attempt.get('status')=='completed' else '当前显示上次已生成报告；最近一次分析'+('仍在进行' if attempt.get('status')=='running' else '未完成')+'，不代表本次请求成功。'
        return report
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,status,data,kind='application/json; charset=utf-8',attachment=False):
            body=json.dumps(data,ensure_ascii=False).encode() if isinstance(data,dict) else data
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            if attachment:self.send_header('Content-Disposition','attachment; filename="'+(attachment if isinstance(attachment,str) else 'course-comments.json')+'"')
            self.end_headers();self.wfile.write(body)
        def valid_host(self):return self.headers.get('Host') in (f'127.0.0.1:{args.port}',f'localhost:{args.port}')
        def media(self,file):
            size=file.stat().st_size;start=0;end=size-1;partial=False
            if self.headers.get('Range'):
                import re
                match=re.fullmatch(r'bytes=(\d+)-(\d*)',self.headers['Range'])
                if not match:return self.send(416,{'error':'不支持该范围'})
                start=int(match[1]);end=min(int(match[2]) if match[2] else end,end);partial=True
                if start>end:return self.send(416,{'error':'范围超出文件'})
            self.send_response(206 if partial else 200);self.send_header('Content-Type','video/mp4')
            self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(end-start+1))
            if partial:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
            self.end_headers()
            try:
                with file.open('rb') as stream:
                    stream.seek(start);remaining=end-start+1
                    while remaining:
                        data=stream.read(min(262144,remaining))
                        if not data:break
                        self.wfile.write(data);remaining-=len(data)
            except ConnectionError:pass
        def do_GET(self):
            if not self.valid_host():return self.send(403,{'error':'仅允许本机访问'})
            parsed=urlparse(self.path);path=parsed.path
            try:
                if path=='/':return self.send(200,(root/'web/index.html').read_text(encoding='utf-8').replace('__TOKEN__',token).encode(),'text/html; charset=utf-8')
                if path in ('/app.js','/style.css'):
                    return self.send(200,(root/'web'/path[1:]).read_bytes(),'text/javascript; charset=utf-8' if path.endswith('.js') else 'text/css; charset=utf-8')
                if path=='/api/model/readiness':
                    from model_access import readiness
                    return self.send(200,readiness(parse_qs(parsed.query).get('provider',['api'])[0]))
                if path=='/api/model/settings':
                    from api_settings import public
                    return self.send(200,public())
                if path=='/api/model/status':
                    from local_model import status
                    from model_providers import settings
                    profiles={}
                    for name in ('api','local','campus'):
                        try:
                            cfg=settings(name);profiles[name]={'configured':True,'model':cfg['model']}
                        except ValueError:profiles[name]={'configured':False}
                    return self.send(200,dict(status(),profiles=profiles))
                if path=='/api/courses':
                    result=[]
                    for record in [root/'outputs/real-acquisition/acquisition.json',*jobs.glob('*/assets/acquisition.json')]:
                        if not record.exists():continue
                        item=public_summary(read_json(record));item['id']='real-acquisition' if record.parent.name=='real-acquisition' else record.parent.parent.name
                        if item.get('artifacts',{}).get('danmaku'):result.append(item)
                    return self.send(200,{'courses':sorted(result,key=lambda x:x.get('observed_at') or '',reverse=True)})
                if path.startswith('/api/workbench/'):
                    parts=path.split('/');assets=folder(parts[3]);out=analysis_dir(assets);action=parts[4]
                    if action=='status':return self.send(200,analysis_status(assets))
                    if action=='review':return self.send(200,read_json(out/'review.json',{'notes':'','items':{}}))
                    if action=='syllabus':return self.send(200,{'syllabus':read_json(out/'syllabus.json')})
                    if action=='report':
                        if not (out/'report.json').exists():return self.send(409,{'error':'尚无已生成报告'})
                        return self.send(200,saved_report(assets))
                    if action=='video':return self.media(assets/'course.mp4')
                    if action=='frame':
                        index=int(parse_qs(parsed.query).get('index',['0'])[0]);manifest=read_json(out/'media/frames.json',[])
                        if not 0<=index<len(manifest):raise ValueError('画面编号无效')
                        image=(out/'media'/manifest[index]['file']).resolve()
                        if not image.is_relative_to((out/'media').resolve()) or image.suffix!='.jpg':raise ValueError('无效画面')
                        return self.send(200,image.read_bytes(),'image/jpeg')
                    if action in ('export','html'):
                        if not (out/'report.json').exists():return self.send(409,{'error':'尚无已生成报告'})
                        report=saved_report(assets);report['teacher_review']=read_json(out/'review.json',{'notes':'','items':{}})
                        if action=='html':
                            from workbench import export_html
                            return self.send(200,export_html(root,report,out/'media').encode(),'text/html; charset=utf-8',attachment='course-feedback.html')
                        return self.send(200,report,attachment='course-feedback.json')
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
            except ConnectionError:return
            except OSError:return self.send(404,{'error':'本地素材暂不可读取'})
        def do_POST(self):
            if not self.valid_host():return self.send(403,{'error':'仅允许本机访问'})
            if self.headers.get('X-Demo-Token')!=token:return self.send(403,{'error':'会话校验失败，请刷新页面'})
            if self.headers.get('Origin') not in (None,f'http://127.0.0.1:{args.port}',f'http://localhost:{args.port}'):
                return self.send(403,{'error':'来源不允许'})
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<8*1024*1024:raise ValueError('请求大小无效')
                data=json.loads(self.rfile.read(n))
                if self.path.startswith('/api/model/'):
                    import api_settings
                    actions={'configure':lambda:api_settings.configure(data),'models':api_settings.models,
                        'select':lambda:api_settings.select_model(data),'probe':api_settings.probe,
                        'balance':api_settings.balance,'clear':api_settings.clear,'probe-vision':lambda:api_settings.probe(True)}
                    action=self.path.rsplit('/',1)[-1]
                    if action not in actions:return self.send(404,{'error':'未知模型操作'})
                    if any(t.is_alive() for t in analysis_workers.values()):return self.send(409,{'error':'分析进行中，请结束后操作模型设置'})
                    try:return self.send(200,actions[action]())
                    except ValueError as exc:return self.send(400,{'error':str(exc)})
                if self.path=='/api/login/start':return self.send(200,login.start())
                if self.path=='/api/login/poll':return self.send(200,login.poll())
                if self.path=='/api/login/clear':return self.send(200,login.clear())
                if self.path=='/api/login/refresh':return self.send(200,login.refresh())
                if self.path.startswith('/api/workbench/'):
                    parts=self.path.split('/');jid=parts[3];assets=folder(jid);out=analysis_dir(assets);out.mkdir(exist_ok=True);action=parts[4]
                    if not (assets/'acquisition.json').exists():raise ValueError('无素材记录')
                    if action=='syllabus':
                        with lock:
                            document=parse_upload(data);save_json(out/'syllabus.json',document)
                        return self.send(200,{'syllabus':document,'saved':True})
                    if action=='review':
                        if not isinstance(data.get('notes'),str) or len(data['notes'])>50000:raise ValueError('记录过长')
                        items=data.get('items',{})
                        report=read_json(out/'report.json',{'comments':[]});ids={c['id'] for c in report['comments']}
                        if not isinstance(items,dict) or not set(items)<=ids or any(v not in ('confirmed','rejected','pending') for v in items.values()):raise ValueError('复核引用无效')
                        save_json(out/'review.json',{'notes':data['notes'],'items':items});return self.send(200,{'saved':True})
                    if action in ('analyze','import'):
                        with lock:
                            if any(t.is_alive() for t in analysis_workers.values()):return self.send(409,{'error':'已有分析任务进行中，请等待完成'})
                            mode=data.get('mode','text')
                            from model_access import require_ready
                            try:require_ready(data.get('provider','api'),'imported' if action=='import' else mode)
                            except ValueError as exc:return self.send(409,{'error':str(exc)})
                            if action=='import':
                                temp=out/'import-check.json';save_json(temp,data.get('transcript',{}))
                                try:
                                    segments=read_transcript(temp,read_json(assets/'acquisition.json')['duration_s'])
                                    if not segments:raise ValueError('转写为空')
                                    temp.replace(out/'imported-transcript.json')
                                finally:
                                    if temp.exists():temp.unlink()
                                mode='imported'
                            if mode not in ('text','multimodal','imported'):raise ValueError('分析模式无效')
                            provider=data.get('provider','api')
                            from model_providers import settings
                            settings(provider)
                            limit=data.get('max_seconds')
                            if limit is not None and (type(limit) is not int or not 0 < limit <= read_json(assets/'acquisition.json')['duration_s']):raise ValueError('分析范围无效')
                            if data.get('sample_size') not in (None,100):raise ValueError('抽样数量无效')
                            save_json(out/'state.json',{'status':'running','stage':'任务准备中','mode':mode})
                            thread=threading.Thread(target=run_analysis,args=(root,assets,mode,limit,provider,data.get('sample_size')),daemon=True);analysis_workers[jid]=thread;thread.start()
                        return self.send(202,{'id':jid})
                    return self.send(404,{'error':'未找到操作'})
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
            except (ValueError,KeyError,IndexError,TypeError,AttributeError):return self.send(400,{'error':'参数无效或响应未通过校验'})
            except ConnectionError:return
            except Exception as exc:return self.send(502,{'error':'服务操作未完成：'+type(exc).__name__})
    print(f'http://127.0.0.1:{args.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()


if __name__=='__main__':main()
