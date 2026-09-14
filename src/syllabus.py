"""Local teacher document intake. Paragraphs are source text, not model objectives."""
import base64
import datetime
import hashlib
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

PLACEHOLDER='【请先连接大模型以获取准确分析】'


def parse_upload(data):
    name=Path(str(data.get('name',''))).name
    suffix=Path(name).suffix.lower()
    if suffix not in ('.txt','.md','.docx'):raise ValueError('支持 TXT、Markdown 和 DOCX 大纲文件')
    try:raw=base64.b64decode(data.get('content',''),validate=True)
    except Exception as exc:raise ValueError('文件编码无效') from exc
    if not raw or len(raw)>5*1024*1024:raise ValueError('文件需非空且不超过5MB')
    if suffix=='.docx':
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                info=archive.getinfo('word/document.xml')
                if info.file_size>16*1024*1024:raise ValueError('文档解压后过大')
                xml=archive.read(info)
            if b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper():raise ValueError('不支持含实体声明的文档')
            tree=ET.fromstring(xml);ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            lines=[''.join(t.text or '' for t in p.findall('.//w:t',ns)).strip() for p in tree.findall('.//w:p',ns)]
        except (zipfile.BadZipFile,KeyError,ET.ParseError) as exc:raise ValueError('无法读取DOCX正文，请另存为标准DOCX或TXT') from exc
    else:
        try:text=raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:text=raw.decode('gb18030')
            except UnicodeDecodeError as exc:raise ValueError('文本编码无法识别，请保存为UTF-8') from exc
        if '\x00' in text:raise ValueError('文件不包含有效纯文本')
        lines=[x.strip() for x in text.splitlines()]
    lines=[x for x in lines if x]
    if not lines:raise ValueError('未读取到大纲正文，图片中的文字需先转成文本')
    if len(lines)>3000 or sum(map(len,lines))>150000:raise ValueError('大纲过长，请仅导入本课程相关部分')
    return {'filename':name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),
            'imported_at':datetime.datetime.now().astimezone().isoformat(),
            'paragraphs':[{'id':f'o{i+1:04d}','text':text} for i,text in enumerate(lines)],
            'paragraph_count':len(lines),'text':'\n'.join(lines),'extraction_method':'原文段落提取，未进行语义归纳'}


def present_report(report,syllabus=None):
    import copy
    r=copy.deepcopy(report)
    r['media_summary']={'transcript_segments':len(report.get('segments',[])),
                        'frames':len(report.get('frames',[])),
                        'status':'已进行本地音视频处理' if report.get('analysis_mode')=='multimodal' else '尚未进行音视频处理'}
    r['syllabus']=syllabus
    if r.get('analysis_status') == 'model_preliminary':
        r['syllabus_stale'] = r.get('syllabus_sha256') != (syllabus['sha256'] if syllabus else None)
        if r['syllabus_stale']:
            r.get('model_review', {})['alignment'] = []
        return r
    r['integrated_evaluation']={'status':'awaiting_model','outline_alignment':PLACEHOLDER,
        'teaching_presentation':PLACEHOLDER,'feedback_interpretation':PLACEHOLDER,'improvement_suggestions':PLACEHOLDER}
    r['analysis_status']='awaiting_model';r['method_note']=PLACEHOLDER
    for c in r.get('comments',[]):
        c.update(labels=[],questions=[],positive=False,candidate_segment_ids=[],association_status=PLACEHOLDER,method=PLACEHOLDER)
    r.update(summary=None,questions=[],groups=[],wordcloud=[],positive_comment_ids=[],question_count=None,segments=[])
    r['label_counts']={k:None for k in r.get('label_counts',{})}
    r['timeline']=[{k:v for k,v in b.items() if k!='question_count'} for b in r.get('timeline',[])]
    return r
