"""Real local analysis jobs; retain evidence and never substitute synthetic input."""
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from course_feedback.pipeline import read_comments, read_transcript, rule_analysis, build_report
from fetch_course import save_json


def read_json(path, default=None):
    for attempt in range(4):
        try:return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
        except (PermissionError,json.JSONDecodeError):
            if attempt==3:raise
            time.sleep(.025)


def run_analysis(root, assets, mode, max_seconds=None, provider="local", sample_size=None):
    started = time.perf_counter()
    out = assets.parent / 'analysis' if assets.name == 'assets' else assets / 'analysis'
    out.mkdir(exist_ok=True)
    state = {'status': 'running', 'mode': mode, 'stage': '校验输入', 'started_at': datetime.datetime.now().astimezone().isoformat()}
    def update(**values):
        state.update(values); save_json(out / 'state.json', state)
    update()
    try:
        record = read_json(assets / 'acquisition.json')
        duration = record['duration_s']
        comments, audit = read_comments(assets / 'course.danmaku.xml', duration)
        if not comments: raise ValueError('当前快照没有可分析弹幕')
        segments = []; frames = []
        media_dir = out / 'media'
        if mode == 'multimodal':
            if not record.get('artifacts', {}).get('video'): raise ValueError('尚未获取可验证的音视频')
            model = Path(os.environ.get('COURSE_ASR_MODEL', str(root / 'data/models/whisper-tiny')))
            if not (model / 'model.bin').exists(): raise ValueError('本地转写模型未安装，请设置 COURSE_ASR_MODEL')
            update(stage='本地音频转写与画面提取', message='处理完整课程；按5分钟分块，可复用已完成分块')
            with (out / 'media-process.log').open('w', encoding='utf-8') as log:
                completed = subprocess.run([sys.executable, str(root/'src/prepare_media.py'), '--media', str(assets/'course.mp4'),
                    '--out', str(media_dir), '--model', str(model), '--frame-seconds', '120'], stdout=log, stderr=log)
            if completed.returncode: raise ValueError('音视频处理失败，详见本机 analysis/media-process.log；可重试或选择弹幕分析')
            segments = read_transcript(media_dir / 'transcript.json', duration)
            frames = read_json(media_dir / 'frames.json', [])
        elif mode == 'imported':
            segments = read_transcript(out / 'imported-transcript.json', duration)
        elif mode != 'text': raise ValueError('未知分析模式')
        source_count = len(comments)
        source_duration = duration
        source_audit = dict(audit)
        if max_seconds is not None:
            if type(max_seconds) not in (int, float) or not 0 < max_seconds <= duration:
                raise ValueError('分析范围无效')
            duration = max_seconds
            comments = [c for c in comments if c['playback_ms'] < duration*1000]
            segments = [s for s in segments if s['end_ms'] <= duration*1000]
            frames = [f for f in frames if f['requested_time_s'] < duration]
            audit = dict(raw_count=len(comments), accepted_count=len(comments), duplicate_count=0, rejected_count=0)
        range_count = len(comments)
        if sample_size is not None:
            if type(sample_size) is not int or sample_size < 1:raise ValueError('抽样数量无效')
            unique = {}
            for c in sorted(comments, key=lambda c:c['playback_ms']):unique.setdefault(c['text'],c)
            pool = list(unique.values())
            n = min(sample_size,len(pool))
            comments = [pool[round(i*(len(pool)-1)/max(1,n-1))] for i in range(n)]
            audit = dict(raw_count=len(comments),accepted_count=len(comments),duplicate_count=0,rejected_count=0)
        audit['source_sha256'] = source_audit.get('source_sha256')
        update(stage='弹幕分类、问题拆分与统计', accepted=len(comments))
        model_config = read_json(root/'data/local-model.json', {})
        use_model = provider in ('api','campus') or model_config.get('enabled', False)
        if use_model:
            from local_model import Client, classify, enrich, status
            if provider == 'local' and not status()['connected']: raise ValueError('本地模型未就绪，请先启动本地模型服务；未降级为规则分析')
            client = Client(out/'model-cache', provider)
            analyses = classify(comments, client, update)
        else:
            analyses = [rule_analysis(c) for c in comments]
        course = {'title': record['title'], 'duration_s': duration, 'source_url': record.get('source_url',''),
                  'data_kind': 'real', 'duration_source': '课程元信息，媒体已另行核验' if record.get('artifacts',{}).get('video') else '课程元信息'}
        report = build_report(course, comments, audit, segments, analyses, 'model' if use_model else 'rules')
        report['analysis_scope'] = dict(start_s=0, end_s=duration, source_duration_s=source_duration, source_comment_count=source_count, selected_comment_count=len(comments), excluded_comment_count=source_count-len(comments), source_audit=source_audit, range_comment_count=range_count, sample_size=sample_size, sampling_method='按原文去重，保留首次播放位置，按时间排序后等间隔选取；仅检验链路，不估计反馈比例' if sample_size else '范围内全部弹幕', transcript_boundary='仅保留结束位置不超过范围终点的转写句段')
        report.update(frames=frames, analysis_mode=mode, observed_at=record.get('observed_at'),
                      method_note='规则基线候选，尚未完成准确率验证；问题概述采用原文摘录，词云使用预设术语表')
        report['summary'] = {'question_comments': sum(bool(c['questions']) for c in report['comments']),
                             'positive_comments': len(report['positive_comment_ids']),
                             'emotion_only': sum('学习情绪' in c['labels'] and not c['questions'] for c in report['comments'])}
        if use_model:
            save_json(out/'feedback-stage.json',dict(report,processing_stage='feedback_parsed_before_summaries',
                method_note='本地模型反馈候选；讲解主题、问题概述和综合复盘尚未完成'))
            report = enrich(report, client, media_dir, read_json(out/'syllabus.json'), update)
        update(stage='核验引用与保存报告')
        save_json(out/'report.json', report)
        update(status='completed', stage='报告已生成', elapsed_s=round(time.perf_counter()-started,3),
               comments=len(comments), questions=len(report['questions']), segments=len(segments), frames=len(frames))
    except Exception as exc:
        update(status='failed', stage='分析未完成', error=str(exc), elapsed_s=round(time.perf_counter()-started,3))


def analysis_dir(assets):
    return assets.parent / 'analysis' if assets.name == 'assets' else assets / 'analysis'


def analysis_status(assets):
    out = analysis_dir(assets)
    state = read_json(out/'state.json', {'status':'idle', 'stage':'尚未分析'})
    progress = read_json(out/'media/media_run.json')
    if state.get('status') == 'running' and progress:
        state['media_progress'] = {'completed_chunks':len(progress.get('chunks',[])), 'duration_s':progress.get('duration_s'),
                                   'frame_status':progress.get('frame_status')}
    return state


def export_html(root, report, media_dir=None):
    import re
    import base64
    data=dict(report,frames=[])
    if media_dir:
        for f in report.get('frames',[]):
            path=(media_dir/f['file']).resolve()
            if not path.is_relative_to(media_dir.resolve()) or path.suffix.lower()!='.jpg':continue
            body=path.read_bytes()
            if len(body)>2*1024*1024 or not body.startswith(b'\xff\xd8'):continue
            data['frames'].append({'id':f['id'],'time_ms':round(f['requested_time_s']*1000),
                'data_url':'data:image/jpeg;base64,'+base64.b64encode(body).decode(),'note':'按播放位置提取的课程画面'})
    template=(root/'web/report.html').read_text(encoding='utf-8')
    style=(root/'web/style.css').read_text(encoding='utf-8')
    style+='''header{padding:32px max(24px,calc((100vw - 1180px)/2));background:transparent}header small,.sub{color:var(--muted)}main{padding-top:24px}.numbers{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}.number{padding:20px;border:1px solid var(--line);border-radius:24px;background:rgba(255,255,255,.06)}.number strong{display:block;color:var(--gold);font-size:30px}.label b{display:block;color:var(--gold);font-size:27px}.bar{flex:1;min-width:0;padding:0;border:0;background:rgba(255,255,255,.35)}.badge,.tag{color:var(--muted)}.positive{border-left:0}.evidence blockquote{background:transparent;border:0}.action{font-size:13px}.two>.panel{overflow:auto}@media(max-width:700px){.numbers{grid-template-columns:1fr 1fr}}'''
    template=re.sub(r'<style>.*?</style>','<style>'+style+'</style>',template,count=1,flags=re.S)
    encoded=json.dumps(data,ensure_ascii=False).replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e')
    template=template.replace('__REPORT_DATA__',encoded)
    template=template.replace("try{$('notes').value=localStorage.getItem(storageKey)||''}catch{}", "$('notes').value=R.teacher_review?.notes||'';")
    return template
