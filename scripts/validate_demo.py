"""Exercise the live local demo over HTTP; no external model calls."""
import json,re,urllib.request,urllib.error,http.cookiejar
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
a=json.loads((ROOT/'data/demo-access.json').read_text(encoding='utf-8'));base=a['base_url'];cid=a['course_id']
class Session:
 def __init__(self,role):
  self.http=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
  self.token=re.search("window.APP_TOKEN='([^']+)'",self.http.open(base).read().decode())[1]
  self.call('/api/platform/login',a[role])
 def call(self,path,data=None,headers=None):
  req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json','X-Demo-Token':self.token,**(headers or {})})
  try:r=self.http.open(req,timeout=60)
  except urllib.error.HTTPError as e:r=e
  body=r.read();kind=r.headers.get('Content-Type','');return r.status,json.loads(body) if 'json' in kind else body
teacher=Session('teacher');student=Session('student');checks={}
def check(name,condition):
 checks[name]=bool(condition)
 if not condition:raise AssertionError(name)
check('teacher_login',teacher.call('/api/platform/me')[1]['user']['role']=='teacher')
check('student_login',student.call('/api/platform/me')[1]['user']['role']=='student')
check('published_course_visible',any(c['id']==cid for c in student.call('/api/platform/courses')[1]['courses']))
code,video=student.call(f'/api/platform/course/{cid}/video',headers={'Range':'bytes=0-255'});check('video_range',code==206 and len(video)==256)
check('student_workbench_denied',student.call(f'/api/workbench/{cid}/report')[0]==403)
check('student_analysis_denied',student.call(f'/api/workbench/{cid}/analyze',{'mode':'multimodal','provider':'local'})[0]==403)
check('local_ready',teacher.call('/api/model/readiness?provider=local')[1]['text_ready'])
check('campus_locked',not teacher.call('/api/model/readiness?provider=campus')[1]['text_ready'])
code,report=teacher.call(f'/api/workbench/{cid}/report')
if code==200:
 check('real_model_report',report['analysis_status']=='model_preliminary' and report['inference_provider']=='local')
 check('all_100',len(report['comments'])==100)
 check('synthetic_marked',report['course']['data_kind']=='synthetic')
 check('media_chain',bool(report['segments'] and report['frames'] and report['chapters']))
 check('question_summaries',all(g.get('summary') for g in report['groups']))
 check('positive_preserved',bool(report['positive_comment_ids']))
 check('outline_integrated',bool(report.get('syllabus')) and bool(report['model_review']['alignment']) and not report.get('syllabus_stale'))
 check('outline_has_dual_evidence',all(any(i.startswith('o') for i in v['evidence_ids']) and any(i.startswith(('k','c')) for i in v['evidence_ids']) for v in report['model_review']['alignment']))
 eid=report['comments'][0]['id'];review={'notes':'演示复核：已检查首条原文与播放位置；模型其他判断仍需人工审核。','items':{eid:'confirmed'}}
 check('review_saved',teacher.call(f'/api/workbench/{cid}/review',review)[0]==200)
 check('review_readback',teacher.call(f'/api/workbench/{cid}/review')[1]['items'][eid]=='confirmed')
 code,export=teacher.call(f'/api/workbench/{cid}/export');check('json_export',code==200 and export['teacher_review']['notes']==review['notes'])
 code,html=teacher.call(f'/api/workbench/{cid}/html');check('html_export',code==200 and b'__REPORT_DATA__' not in html)
 result={'checks':checks,'course_id':cid,'report_counts':{k:len(report[k]) for k in ['comments','questions','groups','segments','frames','chapters','wordcloud']},'state':teacher.call(f'/api/workbench/{cid}/status')[1]}
else:raise AssertionError('Demo report not available; wait for completion or inspect task error')
(ROOT/'outputs/demo-http-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
