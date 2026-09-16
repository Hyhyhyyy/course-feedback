"""Provision explicitly synthetic local demo fixtures, without changing existing accounts."""
import json,secrets,sys,time
from pathlib import Path
import urllib.request,urllib.parse,http.cookiejar
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from teaching_platform import Platform
from fetch_course import save_json
p=Platform(ROOT);dest=ROOT/'data/demo-access.json'
if dest.exists():
 print('Existing local demo setup: '+str(dest));sys.exit(0)
accounts={}
for role,name in [('teacher','课镜演示教师'),('student','课镜演示学生')]:
 with p.connect() as c:
  if c.execute('SELECT 1 FROM users WHERE name=?',(name,)).fetchone():raise RuntimeError('Demo name already exists; refusing to modify existing credentials')
 password='Kejing-'+secrets.token_urlsafe(9);raw=p.auth({'name':name,'password':password},True)
 user=p.user('course_session='+raw)
 with p.connect() as c:c.execute('UPDATE users SET role=? WHERE id=?',(role,user['id']))
 accounts[role]={'name':name,'password':password}
base='http://127.0.0.1:8766';opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));import re
page=opener.open(base).read().decode();token=re.search("window.APP_TOKEN='([^']+)'",page)[1]
def post(path,data,content='application/json'):
 body=json.dumps(data).encode() if content=='application/json' else data
 req=urllib.request.Request(base+path,data=body,headers={'Content-Type':content,'X-Demo-Token':token})
 return json.load(opener.open(req,timeout=60))
post('/api/platform/login',accounts['teacher'])
fixture=ROOT/'outputs/platform-smoke/lesson.mp4'
result=post('/api/platform/upload?'+urllib.parse.urlencode({'title':'【模拟演示】导数定义与条件核查（100条测试反馈）','rights':'owned-or-authorized'}),fixture.read_bytes(),'video/mp4')
cid=result['id'];post(f'/api/platform/course/{cid}/publish',{'published':True})
record=json.loads((p.assets(cid)/'acquisition.json').read_text(encoding='utf-8'));record.update(data_kind='synthetic',fixture_note='自制短视频与100条程序构造测试反馈，仅用于功能演示，不是自然学生研究数据');save_json(p.assets(cid)/'acquisition.json',record)
texts=['为什么这里要取极限？','导数和平均变化率有什么区别？','增量等于零时能直接相除吗？','这里不懂，请再解释一次','这个符号代表什么？','为什么结果是二倍的x？','负数也可以这样计算吗？','需要先满足哪些条件？','可导一定连续吗？','能再举一个反例吗？','这个例子讲得很清楚','终于明白几何意义了','板书很清晰，谢谢老师','希望把适用条件留在屏幕上','有点紧张，没跟上','这里需要区分函数值与变化率','建议推导再慢一点','积分和求导互为逆运算需要条件','讲得很好，但这一段稍微快了','签到']
with p.connect() as c:
 uid=c.execute('SELECT id FROM users WHERE name=?',(accounts['student']['name'],)).fetchone()[0]
 for i in range(100):
  text=f'测试反馈{i+1:03d}：'+texts[i%20]
  c.execute('INSERT INTO comments(course,user_id,text,playback_ms,created,analysis,external_endpoint) VALUES(?,?,?,?,?,?,?)',(cid,uid,text,round((i+.5)/100*record['duration_s']*1000),time.time()-300+i*2,1,''))
p.snapshot(cid,p.user('course_session='+p.auth(accounts['teacher'])))
accounts.update(course_id=cid,base_url=base,fixture=str(fixture),data_kind='synthetic')
save_json(dest,accounts)
print(json.dumps({'course_id':cid,'credentials_file':str(dest),'comments':100},ensure_ascii=False))
