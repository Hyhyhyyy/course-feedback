"""Single-course snapshots with verified artifact summaries and incremental state."""
import argparse
import datetime
import http.cookiejar
import json
import gzip
import zlib
import re
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode
from acquire_course import normalize_url
from course_feedback.pipeline import read_comments, digest


def save_json(path,data):
    import uuid
    path=Path(path);temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        for attempt in range(5):
            try:temporary.replace(path);break
            except PermissionError:
                if attempt==4:raise
                time.sleep(.025)
    finally:
        if temporary.exists():temporary.unlink()


def decode_body(body,encoding):
    encoding=encoding.lower()
    if encoding=='gzip':return gzip.decompress(body)
    if encoding=='deflate':
        try:return zlib.decompress(body)
        except zlib.error:return zlib.decompress(body,-zlib.MAX_WBITS)
    if encoding in ('','identity'):return body
    raise ValueError('尚未支持的传输压缩：'+encoding)


def inspect_video(path):
    import av
    with av.open(str(path)) as media:
        if not media.duration or not media.streams.video or not media.streams.audio:
            raise ValueError('文件必须含可识别的视频、音频和时长')
        video=media.streams.video[0]
        return {'file':path.name,'bytes':path.stat().st_size,'duration_s':media.duration/av.time_base,
                'width':video.width,'height':video.height,'has_audio':True,'sha256':digest(path)}


def fetch(url,out,cookie_file=None,comments_only=False,reuse_existing=False):
    import yt_dlp
    import imageio_ffmpeg
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    url=normalize_url(url);started=time.perf_counter()
    bvid=urlparse(url).path.split('/')[2];part=int(parse_qs(urlparse(url).query)['p'][0])
    log={'observed_at':datetime.datetime.now().astimezone().isoformat(),'source_url':url,'bvid':bvid,'part':part,
         'status':'running','artifacts':{},'stages':[],
         'scope':'当次可获取的弹幕快照；不要求或宣称全部历史',
         'source_record_status':'用途与后续发布条件另行核对，未将用户操作当作平台许可',
         'login_state':'local_session_supplied' if cookie_file else 'no_session_supplied'}
    log_path=out/'acquisition.json'
    jar=http.cookiejar.MozillaCookieJar()
    if cookie_file:jar.load(cookie_file,ignore_discard=True,ignore_expires=False)
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    def save():save_json(log_path,log)
    def stage(name,status,**details):
        existing=next((x for x in log['stages'] if x['name']==name),None)
        if existing is None:existing={'name':name};log['stages'].append(existing)
        existing.update(status=status,**details);save()
    def get(url,target):
        request=urllib.request.Request(url,headers={'User-Agent':'CourseFeedbackResearch/0.1','Referer':'https://www.bilibili.com/'})
        with opener.open(request,timeout=30) as response:
            body=response.read();encoding=response.headers.get('Content-Encoding','').lower()
        body=decode_body(body,encoding)
        target.write_bytes(body)
    save()
    try:
        stage('metadata','running');meta_path=out/'metadata.json'
        if not (reuse_existing and meta_path.exists()):
            get('https://api.bilibili.com/x/web-interface/view?'+urlencode({'bvid':bvid}),meta_path)
        response=json.loads(meta_path.read_text(encoding='utf-8-sig'))
        if response.get('code')!=0:raise ValueError('课程元信息返回代码：'+str(response.get('code')))
        meta=response['data']
        if meta.get('bvid')!=bvid:raise ValueError('课程编号与返回数据不一致')
        if part>len(meta['pages']):raise ValueError('指定分P不存在')
        page=meta['pages'][part-1];duration=float(page['duration']);cid=page['cid']
        log.update(title=meta['title'],duration_s=duration,cid=cid)
        log['artifacts']['metadata']={'file':'metadata.json','title':meta['title'],'duration_s':duration,'cid':cid}
        stage('metadata','completed');stage('danmaku','running')
        comments_path=out/'course.danmaku.xml'
        if not (reuse_existing and comments_path.exists()):get(f'https://comment.bilibili.com/{cid}.xml',comments_path)
        comments,audit=read_comments(comments_path,duration)
        save_json(out/'comments.json',{'comments':comments,'audit':audit})
        log['artifacts']['danmaku']={'file':comments_path.name,'bytes':comments_path.stat().st_size,
            'raw_count':audit['raw_count'],'valid_count':len(comments),'rejected_count':audit['rejected_count'],
            'first_ms':min((x['playback_ms'] for x in comments),default=None),
            'last_ms':max((x['playback_ms'] for x in comments),default=None),'sha256':audit['source_sha256'],
            'coverage':'当次可获取快照'}
        log['comments_path']=str(comments_path);stage('danmaku','completed')
        if comments_only:log['status']='snapshot_acquired'
        else:
            stage('video','running');media=out/'course.mp4'
            if not (reuse_existing and media.exists()):
                class QuietLogger:
                    def debug(self,msg):pass
                    def warning(self,msg):pass
                    def error(self,msg):pass
                options={'format':'bv[vcodec^=avc1][height<=1080]+ba[abr<=100]/bv[height<=1080]+ba/b',
                    'outtmpl':str(out/'course.%(ext)s'),'noplaylist':True,'merge_output_format':'mp4',
                    'ffmpeg_location':imageio_ffmpeg.get_ffmpeg_exe(),'retries':0,'fragment_retries':0,
                    'concurrent_fragment_downloads':1,'socket_timeout':30,'quiet':True,'noprogress':True,'logger':QuietLogger()}
                last=[0.0]
                def progress(info):
                    if time.monotonic()-last[0]>=1 or info['status']=='finished':
                        last[0]=time.monotonic();stage('video','running',downloaded_bytes=info.get('downloaded_bytes'),
                            total_bytes=info.get('total_bytes') or info.get('total_bytes_estimate'))
                options['progress_hooks']=[progress]
                if cookie_file:options['cookiefile']=str(Path(cookie_file).resolve())
                with yt_dlp.YoutubeDL(options) as ydl:info=ydl.extract_info(url,download=True)
                if info.get('_type')=='playlist':raise ValueError('返回了多视频列表')
            stage('video_validation','running');video=inspect_video(media)
            if abs(video['duration_s']-duration)>3:raise ValueError('媒体时长与课程分P不一致')
            log['artifacts']['video']=video;log['media_path']=str(media)
            stage('video','completed');stage('video_validation','completed');log['status']='acquired'
    except Exception as exc:
        for s in log['stages']:
            if s['status']=='running':s['status']='failed'
        message=re.sub(r'https?://\S+','[请求地址]',str(exc))
        log.update(status='partial' if log['artifacts'] else 'acquisition_failed',error_type=type(exc).__name__,error=message[:600])
    log['elapsed_s']=round(time.perf_counter()-started,3);save();return log


def public_summary(log):
    """Allowlist keeps local paths, credential files and raw responses off the page."""
    return {k:log.get(k) for k in ('status','title','bvid','part','duration_s','observed_at','artifacts','stages','error','elapsed_s','scope','login_state')}


def main():
    p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--out',required=True)
    p.add_argument('--cookie-file');p.add_argument('--comments-only',action='store_true');p.add_argument('--reuse-existing',action='store_true')
    a=p.parse_args();result=fetch(a.url,a.out,a.cookie_file,a.comments_only,a.reuse_existing)
    print(json.dumps(public_summary(result),ensure_ascii=True))
    return 0 if result['status'] in ('acquired','snapshot_acquired') else 1


if __name__=='__main__':raise SystemExit(main())
