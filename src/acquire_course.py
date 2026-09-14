"""Acquire an allowed Bilibili snapshot using yt-dlp; never export browser credentials."""
import argparse
import datetime
import json
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode


def normalize_url(url):
    u=urlparse(url.strip())
    if u.scheme!='https' or u.hostname not in ('www.bilibili.com','bilibili.com') or u.username or u.password or u.port:
        raise ValueError('仅接受https://www.bilibili.com/video/BV...课程地址')
    match=re.fullmatch(r'/video/(BV[0-9A-Za-z]{10})/?',u.path)
    if not match:raise ValueError('需要完整BV视频地址，短链接请先在浏览器打开')
    part=parse_qs(u.query).get('p',['1'])[0]
    if not part.isdigit() or int(part)<1:raise ValueError('分P参数无效')
    return 'https://www.bilibili.com/video/'+match[1]+'/?'+urlencode({'p':int(part)})


def acquire(url,out,access_record,cookie_file=None):
    import yt_dlp
    import imageio_ffmpeg
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    url=normalize_url(url)
    # The record documents a real permission arrangement; its existence is not legal verification.
    if not access_record or not Path(access_record).is_file():
        raise ValueError('需在本地配置对应素材取得与处理范围的记录')
    events=[]
    def progress(data):
        if data['status']=='finished':events.append({'stage':'download_file','status':'completed'})
    options={'format':'bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best',
             'outtmpl':str(out/'course.%(ext)s'),'noplaylist':True,'playlist_items':'1',
             'writesubtitles':True,'subtitleslangs':['danmaku'],'subtitlesformat':'xml',
             'merge_output_format':'mp4','ffmpeg_location':imageio_ffmpeg.get_ffmpeg_exe(),
             'retries':0,'fragment_retries':0,'concurrent_fragment_downloads':1,'socket_timeout':30,
             'quiet':True,'noprogress':True,'progress_hooks':[progress]}
    if cookie_file:
        if not Path(cookie_file).is_file():raise ValueError('本地登录会话文件不存在')
        options['cookiefile']=str(Path(cookie_file).resolve())
    log={'observed_at':datetime.datetime.now().astimezone().isoformat(),'source_url':url,
         'status':'running','coverage':'unknown','events':events,'login_state':'unverified'}
    try:
        with yt_dlp.YoutubeDL(options) as ydl:info=ydl.extract_info(url,download=True)
        if info.get('_type')=='playlist':raise ValueError('返回多视频列表，尚未确定指定分P')
        media=next((p for p in (out/'course.mp4',out/'course.webm',out/'course.mkv') if p.exists()),None)
        comments=out/'course.danmaku.xml'
        if media is None or not comments.is_file():raise ValueError('媒体或弹幕快照未完整取得')
        log.update(status='acquired',title=info.get('title'),duration_s=info.get('duration'),
                   platform_video_id=info.get('id'),media_path=str(media),comments_path=str(comments),
                   scope='yt-dlp返回的弹幕XML快照；未保证平台全历史或全部分片覆盖')
    except Exception as exc:
        log.update(status='acquisition_failed',error_type=type(exc).__name__,
                   error='取得失败；检查访问限制、登录会话及素材范围。失败后停止，不自动绕过。')
    (out/'acquisition.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
    if log['status']!='acquired':raise RuntimeError(log['error'])
    return log


def main():
    p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--out',required=True)
    p.add_argument('--access-record',required=True);p.add_argument('--cookie-file')
    a=p.parse_args();result=acquire(a.url,a.out,a.access_record,a.cookie_file)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
