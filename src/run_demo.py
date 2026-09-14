import argparse
import base64
import datetime
import html
import json
import math
import sys
import time
from pathlib import Path
from course_feedback.pipeline import read_comments, read_transcript, rule_analysis, build_report, digest


def main():
    p = argparse.ArgumentParser(description='Import real or explicitly synthetic inputs and generate an evidence report')
    p.add_argument('--comments', required=True)
    p.add_argument('--transcript', required=True)
    p.add_argument('--frames', help='prepare_media.py生成的frames.json')
    p.add_argument('--duration', type=float, required=True)
    p.add_argument('--title', required=True)
    p.add_argument('--source-url', default='')
    p.add_argument('--duration-source', choices=['declared','media_verified'], default='declared')
    p.add_argument('--data-kind', choices=['real','synthetic'], required=True)
    p.add_argument('--method', choices=['rules','model'], default='rules')
    p.add_argument('--model-url'); p.add_argument('--model')
    p.add_argument('--out', required=True)
    args = p.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    log = {'observed_at': datetime.datetime.now().astimezone().isoformat(), 'data_kind': args.data_kind,
           'method': args.method, 'status': 'running', 'stages': [], 'model_calls_requested':0, 'model_calls_completed': 0}
    model_events=[]
    def model_event(item):
        model_events.append(item)
        if item['state']=='requested':log['model_calls_requested']+=1
        if item['state']=='response_received':log['model_calls_completed']+=1
        (out/'model_batches.json').write_text(json.dumps(model_events,ensure_ascii=False,indent=2),encoding='utf-8')
    def stage(name, **info):
        log['stages'].append({'name': name, 'status': 'completed', **info})
    try:
        if not math.isfinite(args.duration) or args.duration <= 0: raise ValueError('时长必须是正数')
        comments, audit = read_comments(args.comments, args.duration)
        if not comments: raise ValueError('没有可分析弹幕')
        stage('comment_import', accepted=len(comments), rejected=audit['rejected_count'])
        segments = read_transcript(args.transcript, args.duration)
        if not segments: raise ValueError('没有有效转写片段')
        stage('transcript_import', segments=len(segments), sha256=digest(args.transcript))
        if args.method == 'model':
            if not args.model_url or not args.model: raise ValueError('模型模式需指定服务地址和模型名')
            from course_feedback.models import classify
            analyses = classify(comments, args.model_url, args.model,model_event)
        else: analyses = [rule_analysis(c) for c in comments]
        stage('feedback_analysis', method=args.method)
        course = {'title': args.title, 'duration_s': args.duration, 'source_url': args.source_url,
                  'data_kind': args.data_kind, 'duration_source': '本地媒体解码读取' if args.duration_source=='media_verified' else '用户指定，未以媒体核验'}
        report = build_report(course, comments, audit, segments, analyses, args.method)
        report['frames']=[]
        if args.frames:
            frame_manifest=Path(args.frames).resolve()
            for frame in json.loads(frame_manifest.read_text(encoding='utf-8')):
                image_path=(frame_manifest.parent/frame['file']).resolve()
                if not image_path.is_relative_to(frame_manifest.parent) or image_path.suffix.lower() not in ('.jpg','.jpeg'):
                    raise ValueError('关键帧必须是素材目录内的JPEG文件')
                data=image_path.read_bytes()
                if not data.startswith(b'\xff\xd8') or len(data)>2*1024*1024:raise ValueError('关键帧格式或大小不合适')
                t=float(frame['requested_time_s'])
                if not math.isfinite(t) or not 0<=t<=args.duration:raise ValueError('关键帧时间无效')
                report['frames'].append({'id':frame['id'],'time_ms':round(t*1000),
                    'data_url':'data:image/jpeg;base64,'+base64.b64encode(data).decode(),
                    'note':'附近画面，仅供人工核查；尚未用于模型解释'})
            stage('frame_import',frames=len(report['frames']))
        stage('report_validation', questions=report['question_count'])
        encoded = json.dumps(report, ensure_ascii=False, indent=2)
        template = (Path(__file__).resolve().parents[1]/'web/report.html').read_text(encoding='utf-8')
        embedded = encoded.replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
        (out/'report.json').write_text(encoded, encoding='utf-8')
        (out/'index.html').write_text(template.replace('__REPORT_DATA__', embedded), encoding='utf-8')
        log['status'] = 'demo_completed'
        log['scope'] = '弹幕、转写及可选关键帧导入到交互报告；本阶段未执行媒体下载、ASR或视觉理解'
        stage('html_report_written')
    except Exception as exc:
        log['status'] = 'failed'; log['error_type'] = type(exc).__name__; log['error'] = str(exc)
        (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><h1>本次分析失败</h1><p>'+html.escape(str(exc))+'</p><p>请查看run.json。本页未展示上一次结果。</p>',encoding='utf-8')
        (out/'report.json').write_text(json.dumps({'status':'failed','error_type':type(exc).__name__}),encoding='utf-8')
    finally:
        log['elapsed_s'] = round(time.perf_counter()-started, 3)
        (out/'run.json').write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(log, ensure_ascii=False))
    return 0 if log['status'] == 'demo_completed' else 1


if __name__ == '__main__': sys.exit(main())
