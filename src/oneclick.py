"""One command orchestrator; writes state after each actual stage."""
import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path
from acquire_course import acquire


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--url',required=True);p.add_argument('--out',required=True)
    p.add_argument('--access-record',required=True);p.add_argument('--cookie-file')
    p.add_argument('--asr-model',default='small')
    p.add_argument('--method',choices=['rules','model'],default='model')
    p.add_argument('--model-url');p.add_argument('--model')
    a=p.parse_args();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
    log={'observed_at':datetime.datetime.now().astimezone().isoformat(),'status':'running','stages':[]}
    def save(): (out/'job.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
    def step(name,command):
        log['stages'].append({'name':name,'status':'running'});save()
        subprocess.run(command,check=True)
        log['stages'][-1]['status']='completed';save()
    try:
        if a.method=='model' and (not a.model_url or not a.model):raise ValueError('模型模式需先配置模型地址和名称')
        log['stages'].append({'name':'acquisition','status':'running'});save()
        assets=acquire(a.url,out/'assets',a.access_record,a.cookie_file)
        log['stages'][-1]['status']='completed';save()
        source=Path(__file__).parent
        step('media_preparation',[sys.executable,str(source/'prepare_media.py'),'--media',assets['media_path'],
                                 '--model',a.asr_model,'--out',str(out/'media')])
        media_log=json.loads((out/'media/media_run.json').read_text(encoding='utf-8'))
        command=[sys.executable,str(source/'run_demo.py'),'--comments',assets['comments_path'],
                 '--transcript',str(out/'media/transcript.json'),'--duration',str(media_log['duration_s']),
                 '--frames',str(out/'media/frames.json'),
                 '--title',assets['title'],'--source-url',assets['source_url'],'--data-kind','real',
                 '--duration-source','media_verified',
                 '--method',a.method,'--out',str(out/'report')]
        if a.method=='model':command+=['--model-url',a.model_url,'--model',a.model]
        step('report',command)
        log.update(status='demo_completed',report=str(out/'report/index.html'),
                   scope='媒体与弹幕快照取得、ASR、取帧、标注与报告；画面尚未参与语义核验，弹幕历史覆盖未知')
    except Exception as exc:
        log.update(status='failed',error_type=type(exc).__name__,error=str(exc))
        if log['stages'] and log['stages'][-1]['status']=='running':log['stages'][-1]['status']='failed'
    save();print(json.dumps(log,ensure_ascii=False));return 0 if log['status']=='demo_completed' else 1


if __name__=='__main__':raise SystemExit(main())
