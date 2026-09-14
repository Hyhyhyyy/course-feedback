"""Owned-course platform storage. Local pilot only; isolated teacher ownership and published courses."""
import hashlib,hmac,json,math,secrets,sqlite3,time,uuid
from pathlib import Path
from contextlib import contextmanager
from http.cookies import SimpleCookie
from fetch_course import save_json,inspect_video

class Platform:
    def __init__(self,root):
        self.root=Path(root);(self.root/'data').mkdir(exist_ok=True)
        self.db=self.root/'data/platform.db'
        with self.connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT UNIQUE,password TEXT,role TEXT);
            CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT,expires REAL);
            CREATE TABLE IF NOT EXISTS courses(id TEXT PRIMARY KEY,owner TEXT,title TEXT,code TEXT UNIQUE,published INTEGER DEFAULT 0,rights TEXT,created REAL);
            CREATE TABLE IF NOT EXISTS comments(id INTEGER PRIMARY KEY AUTOINCREMENT,course TEXT,user_id TEXT,text TEXT,playback_ms INTEGER,created REAL,analysis INTEGER DEFAULT 0,hidden INTEGER DEFAULT 0);
            ''')
            if 'external_endpoint' not in [r[1] for r in c.execute('PRAGMA table_info(comments)')]:c.execute("ALTER TABLE comments ADD COLUMN external_endpoint TEXT DEFAULT ''")
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.db,timeout=15);c.row_factory=sqlite3.Row
        try:
            with c:yield c
        finally:c.close()
    def user(self,cookie):
        try:
            jar=SimpleCookie();jar.load(cookie or '');raw=jar['course_session'].value
        except (KeyError,ValueError):return None
        key=hashlib.sha256(raw.encode()).hexdigest()
        with self.connect() as c:
            row=c.execute('SELECT u.id,u.name,u.role FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token=? AND s.expires>?',(key,time.time())).fetchone()
        return dict(row) if row else None
    def auth(self,data,register=False):
        name=str(data.get('name','')).strip();password=str(data.get('password',''))
        if not 2<=len(name)<=40 or not 10<=len(password)<=128:raise ValueError('昵称需2—40字，密码需10—128位')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if register:
                if c.execute('SELECT 1 FROM users WHERE name=?',(name,)).fetchone():raise ValueError('昵称已被使用')
                role='student' if c.execute('SELECT 1 FROM users').fetchone() else 'teacher'
                salt=secrets.token_hex(16);digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),310000).hex()
                uid=uuid.uuid4().hex;c.execute('INSERT INTO users VALUES(?,?,?,?)',(uid,name,salt+':'+digest,role))
            else:
                row=c.execute('SELECT * FROM users WHERE name=?',(name,)).fetchone()
                if not row:raise ValueError('昵称或密码错误')
                salt,digest=row['password'].split(':')
                if not hmac.compare_digest(digest,hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),310000).hex()):raise ValueError('昵称或密码错误')
                uid=row['id']
            raw=secrets.token_urlsafe(32);c.execute('DELETE FROM sessions WHERE expires<?',(time.time(),));c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(raw.encode()).hexdigest(),uid,time.time()+43200))
        return raw
    def logout(self,cookie):
        try:
            jar=SimpleCookie();jar.load(cookie or '');key=hashlib.sha256(jar['course_session'].value.encode()).hexdigest()
            with self.connect() as c:c.execute('DELETE FROM sessions WHERE token=?',(key,))
        except KeyError:pass
    def assets(self,cid):
        if len(cid)!=32 or any(x not in '0123456789abcdef' for x in cid):raise ValueError('课程编号无效')
        return self.root/'outputs/jobs'/cid/'assets'
    def course(self,cid,user,owner=False):
        with self.connect() as c:
            row=c.execute('SELECT * FROM courses WHERE id=?',(cid,)).fetchone()
            if not row:raise ValueError('课程不存在')
            if not user:raise PermissionError('请先登录')
            owned=row['owner']==user['id']
            if not owned and (owner or not row['published']):raise PermissionError('无权访问该课程')
        return dict(row)
    def exists(self,cid):
        with self.connect() as c:return bool(c.execute('SELECT 1 FROM courses WHERE id=?',(cid,)).fetchone())
    def listing(self,user):
        with self.connect() as c:
            rows=c.execute('SELECT * FROM courses WHERE owner=? OR published=1 ORDER BY created DESC',(user['id'],)).fetchall()
            result=[]
            for row in rows:
                d=dict(row);d['owned']=d['owner']==user['id'];d.pop('owner');d.pop('rights');
                d.pop('code')
                d['comment_count']=c.execute('SELECT COUNT(*) FROM comments WHERE course=? AND hidden=0',(d['id'],)).fetchone()[0]
                result.append(d)
        return result
    def upload(self,user,title,rights,stream,size):
        if user['role']!='teacher':raise PermissionError('仅教师可上传')
        if not 1<=len(title.strip())<=150 or rights!='owned-or-authorized':raise ValueError('请填写标题并确认素材权利')
        if not 0<size<=512*1024*1024:raise ValueError('视频上限512MB')
        cid=uuid.uuid4().hex;assets=self.assets(cid);assets.mkdir(parents=True);temp=assets/'upload.part'
        try:
            with temp.open('wb') as f:
                remaining=size
                while remaining:
                    block=stream.read(min(1024*1024,remaining))
                    if not block:raise ValueError('上传中断，请重试')
                    f.write(block);remaining-=len(block)
            # Only MP4 container is accepted; browser playback suitability is checked separately.
            with temp.open('rb') as f:header=f.read(32)
            if header[4:8]!=b'ftyp':raise ValueError('请上传MP4文件')
            import av
            with av.open(str(temp)) as v:
                if not v.streams.video or v.streams.video[0].codec_context.name!='h264':raise ValueError('当前支持H.264编码的MP4视频')
                if v.streams.audio and v.streams.audio[0].codec_context.name!='aac':raise ValueError('当前音轨需为AAC编码')
            info=inspect_video(temp);temp.replace(assets/'course.mp4');info['file']='course.mp4'
            with self.connect() as c:c.execute('INSERT INTO courses VALUES(?,?,?,?,?,?,?)',(cid,user['id'],title.strip(),secrets.token_hex(5).upper(),0,rights,time.time()))
            save_json(assets/'acquisition.json',dict(source_kind='platform',title=title.strip(),duration_s=info['duration_s'],status='acquired',observed_at=time.strftime('%Y-%m-%dT%H:%M:%S'),artifacts={'metadata':{'duration_s':info['duration_s']},'video':info,'danmaku':{'valid_count':0}},stages=[],scope='平台课程；分析使用已同意的弹幕固定快照'))
            self.snapshot(cid,user)
            return cid
        except Exception:
            if temp.exists():temp.unlink()
            raise
    def publish(self,cid,user,published):
        self.course(cid,user,True)
        if type(published) is not bool:raise ValueError('发布状态无效')
        with self.connect() as c:c.execute('UPDATE courses SET published=? WHERE id=?',(int(published),cid))
    def comments(self,cid,user):
        self.course(cid,user)
        with self.connect() as c:rows=c.execute('SELECT id,user_id,text,playback_ms,created,analysis FROM comments WHERE course=? AND hidden=0 ORDER BY id LIMIT 20000',(cid,)).fetchall()
        return [dict(id=r['id'],text=r['text'],playback_ms=r['playback_ms'],mine=r['user_id']==user['id'],analysis=bool(r['analysis'])) for r in rows]
    def post_comment(self,cid,user,data):
        self.course(cid,user);text=str(data.get('text','')).strip();t=data.get('playback_ms')
        duration=json.loads((self.assets(cid)/'acquisition.json').read_text(encoding='utf-8'))['duration_s']
        if not 1<=len(text)<=300 or type(t) not in (float,int) or not math.isfinite(t) or not 0<=t<=duration*1000:raise ValueError('弹幕文字或播放时间无效')
        if type(data.get('analysis',False)) is not bool:raise ValueError('分析选项无效')
        endpoint=''
        if data.get('external') is True:
            if data.get('analysis') is not True:raise ValueError('请先同意反馈分析')
            endpoint=external_service()['url']
            if not endpoint or data.get('external_endpoint')!=endpoint:raise ValueError('外部模型服务已变更，请重新阅读分析说明')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            last=c.execute('SELECT MAX(created) FROM comments WHERE user_id=?',(user['id'],)).fetchone()[0]
            if last and time.time()-last<2:raise ValueError('请间隔2秒再发送')
            c.execute('INSERT INTO comments(course,user_id,text,playback_ms,created,analysis,external_endpoint) VALUES(?,?,?,?,?,?,?)',(cid,user['id'],text,round(t),time.time(),int(data.get('analysis',False)),endpoint))
    def withdraw(self,cid,user,comment_id):
        course=self.course(cid,user)
        with self.connect() as c:
            r=c.execute('SELECT user_id FROM comments WHERE id=? AND course=?',(comment_id,cid)).fetchone()
            if not r or (r['user_id']!=user['id'] and course['owner']!=user['id']):raise PermissionError('只能撤回自己的弹幕，教师可隐藏本课弹幕')
            c.execute('UPDATE comments SET hidden=1,analysis=0 WHERE id=?',(comment_id,))
        # Existing snapshots/reports are invalidated without deleting raw research files.
        out=self.assets(cid).parent/'analysis';out.mkdir(exist_ok=True)
        save_json(out/'withdrawal.json',{'at':time.time(),'reason':'弹幕已撤回；请重新生成报告，旧报告暂停访问'})
    def snapshot(self,cid,user,endpoint=None):
        self.course(cid,user,True)
        import xml.etree.ElementTree as ET
        assets=self.assets(cid);tree=ET.Element('i');mapping=[]
        with self.connect() as c:rows=c.execute('SELECT id,text,playback_ms FROM comments WHERE course=? AND hidden=0 AND analysis=1 ORDER BY id',(cid,)).fetchall()
        if endpoint is not None:
            with self.connect() as c:allowed={r[0] for r in c.execute('SELECT id FROM comments WHERE course=? AND external_endpoint=?',(cid,endpoint))}
            rows=[r for r in rows if r['id'] in allowed]
        for i,r in enumerate(rows):
            node=ET.SubElement(tree,'d',p=f"{r['playback_ms']/1000},1,25,16777215,0,0,0,{r['id']}");node.text=r['text'];mapping.append({'evidence_id':f'c{i+1:06d}','platform_comment_id':r['id']})
        xml=assets/'course.danmaku.xml';tmp=assets/'snapshot.tmp';tmp.write_bytes(ET.tostring(tree,encoding='utf-8'));tmp.replace(xml)
        from course_feedback.pipeline import read_comments
        record=json.loads((assets/'acquisition.json').read_text(encoding='utf-8'));comments,audit=read_comments(xml,record['duration_s'])
        save_json(assets/'comments.json',{'comments':comments});save_json(assets/'platform-snapshot.json',{'created':time.time(),'count':len(rows),'mapping':mapping,'sha256':audit['source_sha256']})
        record['artifacts']['danmaku']={'valid_count':len(comments)};record['observed_at']=time.strftime('%Y-%m-%dT%H:%M:%S');save_json(assets/'acquisition.json',record)
        return {'count':len(comments)}


def external_service():
    from api_settings import snapshot
    try:
        cfg=snapshot(False)
        return {'url':cfg['url'],'vendor':cfg['vendor']}
    except ValueError:return {'url':'','vendor':''}
