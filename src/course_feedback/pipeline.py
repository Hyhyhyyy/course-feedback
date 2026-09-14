import csv
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

LABELS = ['问题与求助', '知识交流', '理解自述', '学习情绪', '教学评价', '改进建议']
QUESTION = re.compile(r'[?？]|为什么|怎么|如何|求解|求助|没懂|不懂|看不懂|听不懂|跟不上|不明白|能不能|能否|有没有|啥意思|什么意思|咋')
TERMS = ['导数定义','导数','极限','连续','可导','增量','分母','约分','左右导数','函数','例题','证明','公式','定义域','步骤','速度','板书','声音']


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def redact(text):
    text = re.sub(r'(?<!\d)1[3-9]\d{9}(?!\d)', '[电话已隐藏]', str(text))
    return re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[邮箱已隐藏]', text)


def read_comments(path, duration):
    """Explicit units: XML p[0] seconds; normalized JSON/CSV playback_ms."""
    path = Path(path)
    if path.suffix.lower() == '.xml':
        raw = path.read_text(encoding='utf-8-sig')
        if '<!DOCTYPE' in raw.upper() or '<!ENTITY' in raw.upper():
            raise ValueError('XML不得包含DTD或实体声明')
        rows = []
        for el in ET.fromstring(raw).iter('d'):
            fields = el.attrib.get('p', '').split(',')
            rows.append({'playback_s': fields[0], 'text': el.text or '',
                         'source_id': fields[7] if len(fields) > 7 else ''})
    elif path.suffix.lower() == '.csv':
        with path.open(encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
    elif path.suffix.lower() == '.json':
        rows = json.loads(path.read_text(encoding='utf-8-sig'))
        if isinstance(rows, dict):
            rows = rows['comments']
    else:
        raise ValueError('弹幕文件支持JSON、CSV或B站d/p结构XML')
    if not isinstance(rows, list):
        raise ValueError('弹幕输入必须为记录数组')
    comments, rejected, duplicate_ids, seen = [], [], [], {}
    for i, row in enumerate(rows):
        try:
            t = float(row['playback_ms']) if 'playback_ms' in row else float(row['playback_s']) * 1000
            if not math.isfinite(t) or t < 0 or t > duration * 1000:
                raise ValueError('播放时间超出课程区间或无效')
            text = redact(row['text']).strip()
            if not text:
                raise ValueError('空文本')
            sid = str(row.get('source_id') or '')
            if sid and sid in seen:
                if seen[sid] != (t, text):
                    raise ValueError('相同来源编号对应冲突内容')
                duplicate_ids.append(i)
                continue
            if sid:
                seen[sid] = (t, text)
            comments.append({'id': f'c{i+1:06d}', 'playback_ms': round(t), 'text': text,
                             'source_row': i+1})
        except (KeyError, TypeError, ValueError) as exc:
            rejected.append({'source_row': i+1, 'reason': str(exc)})
    return comments, {'raw_count': len(rows), 'accepted_count': len(comments),
                      'duplicate_count': len(duplicate_ids), 'rejected': rejected,
                      'rejected_count': len(rejected), 'source_sha256': digest(path),
                      'coverage': 'unknown', 'privacy': '仅自动隐藏电话和邮箱；仍需人工复核其他个人信息'}


def read_transcript(path, duration):
    """Accept FrameScope TranscriptResult or NoteResult JSON; validate every segment."""
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    data = data.get('transcript', data)
    result = []
    for i, seg in enumerate(data['segments']):
        start, end = float(seg['start']), float(seg['end'])
        if not all(math.isfinite(x) for x in (start, end)) or not 0 <= start < end <= duration + 0.1:
            raise ValueError(f'转写片段{i+1}时间无效')
        result.append({'id': f's{i+1:06d}', 'start_ms': round(start*1000),
                       'end_ms': round(end*1000), 'text': redact(seg['text'])})
    return sorted(result, key=lambda x: x['start_ms'])


def rule_analysis(comment):
    """Debug baseline only; no calibrated accuracy or psychological-state inference."""
    text = comment['text']
    labels = []
    if QUESTION.search(text): labels.append(LABELS[0])
    if any(x in text for x in TERMS) and re.search(r'因为|所以|等于|应该|可以|注意', text): labels.append(LABELS[1])
    if re.search(r'懂了|明白了|理解了|会了|没懂|不懂|跟不上', text): labels.append(LABELS[2])
    if re.search(r'崩溃|烦|开心|痛苦|焦虑|救命|绝望|哈哈|太难|晕', text): labels.append(LABELS[3])
    if re.search(r'讲得|讲的|讲解|清楚|清晰|老师|声音|板书|太快|太慢', text): labels.append(LABELS[4])
    if re.search(r'建议|希望|能不能|能否|再讲|慢一点|大一点|补充', text): labels.append(LABELS[5])
    questions = []
    for part in re.split(r'(?<=[?？。！!；;])', text):
        part = part.strip()
        if QUESTION.search(part):
            kind = '具体提问' if re.search(r'[?？]|为什么|怎么|如何|能否|能不能', part) else '笼统求助'
            questions.append({'text': part, 'kind': kind})
    return {'id': comment['id'], 'labels': labels, 'questions': questions,
            'positive': bool(re.search(r'讲得好|讲的好|清楚|清晰|谢谢|太棒|懂了|明白了', text)),
            'method': '规则基线，需人工核查'}


def associate(comment, segments):
    t = comment['playback_ms']
    candidates = [s for s in segments if s['end_ms'] >= t-60000 and s['start_ms'] <= t+15000]
    terms = {w for w in TERMS if w in comment['text']}
    ranked = sorted(candidates, key=lambda s: (-sum(w in s['text'] for w in terms), abs(s['start_ms']-t)))
    # Candidate retrieval is not a validated knowledge-point assignment.
    return {'candidate_segment_ids': [s['id'] for s in ranked[:3]],
            'association_status': '候选片段待核查' if ranked else '未找到候选片段'}


def build_report(course, comments, audit, segments, analyses, mode):
    if {x['id'] for x in analyses} != {x['id'] for x in comments} or len(analyses) != len(comments):
        raise ValueError('分类输出未覆盖输入或出现重复编号')
    amap = {x['id']: x for x in analyses}
    questions, groups, feedback = [], {}, []
    for comment in comments:
        item = dict(comment)
        item.update(amap[item['id']]); item.update(associate(comment, segments))
        feedback.append(item)
        for q in item['questions']:
            unit = {'id': f'q{len(questions)+1:06d}', 'comment_id': item['id'],
                    'text': q['text'], 'kind': q['kind'],
                    'candidate_segment_ids': item['candidate_segment_ids']}
            questions.append(unit)
            # Exact normalized text groups preserve differing mathematical conditions.
            key = re.sub(r'\s+', '', unit['text'])
            if key not in groups: groups[key] = {'title': unit['text'], 'question_ids': [], 'comment_ids': []}
            groups[key]['question_ids'].append(unit['id'])
            if item['id'] not in groups[key]['comment_ids']: groups[key]['comment_ids'].append(item['id'])
    for i, group in enumerate(groups.values()):
        group.update(id=f'g{i+1:06d}', count=len(group['question_ids']), summary=group['title'],
                     summary_method='原问题摘录；仅合并空白差异相同的问题')
    labels = {label: sum(label in x['labels'] for x in feedback) for label in LABELS}
    bins = [{'start_ms': i*60000, 'end_ms': min((i+1)*60000, round(course['duration_s']*1000)),
             'count': 0, 'question_count': 0} for i in range(math.ceil(course['duration_s']/60))]
    for item in feedback:
        b = bins[min(item['playback_ms']//60000, len(bins)-1)]
        b['count'] += 1; b['question_count'] += len(item['questions'])
    terms = Counter(w for q in questions for w in TERMS if w in q['text'])
    cloud = [{'term': w, 'count': n, 'question_ids': [q['id'] for q in questions if w in q['text']]}
             for w, n in terms.most_common()]
    report = {'schema_version': 1, 'course': course, 'mode': mode,
              'audit': audit, 'comments': feedback, 'segments': segments,
              'questions': questions, 'groups': list(groups.values()), 'wordcloud': cloud,
              'label_counts': labels, 'timeline': bins, 'question_count': len(questions),
              'positive_comment_ids': [x['id'] for x in feedback if x['positive']],
              'limitations': ['统计仅针对导入快照；全历史覆盖未知', '类别允许重叠，不相加为总人数',
                              '候选片段尚未经过视觉与语义核验', '问题摘录和规则标签不代表已验证的教学评价']}
    validate_report(report)
    return report


def validate_report(report):
    comments = {c['id'] for c in report['comments']}
    segments = {s['id'] for s in report['segments']}
    questions = {q['id'] for q in report['questions']}
    for q in report['questions']:
        if q['comment_id'] not in comments or not set(q['candidate_segment_ids']) <= segments:
            raise ValueError('问题引用不存在')
    memberships = [qid for g in report['groups'] for qid in g['question_ids']]
    if set(memberships) != questions or len(memberships) != len(questions):
        raise ValueError('问题归组发生丢失或重复')
    if sum(b['count'] for b in report['timeline']) != len(comments):
        raise ValueError('时间轴计数不一致')
    audit = report['audit']
    if audit['raw_count'] != audit['accepted_count'] + audit['duplicate_count'] + audit['rejected_count']:
        raise ValueError('导入数量不守恒')
    return True
