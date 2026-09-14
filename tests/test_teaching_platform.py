import io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from teaching_platform import Platform
from course_av import boundary_candidates

class PlatformTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.p=Platform(self.root)
  raw=self.p.auth({'name':'teacher','password':'long-password'},True);self.t=self.p.user('course_session='+raw)
  raw=self.p.auth({'name':'student','password':'long-password'},True);self.s=self.p.user('course_session='+raw)
  self.cid='a'*32;assets=self.p.assets(self.cid);assets.mkdir(parents=True)
  from fetch_course import save_json
  save_json(assets/'acquisition.json',{'duration_s':60,'artifacts':{}})
  with self.p.connect() as c:c.execute('INSERT INTO courses VALUES(?,?,?,?,?,?,?)',(self.cid,self.t['id'],'课程','unused',0,'owned-or-authorized',1))
 def tearDown(self):self.temp.cleanup()
 def test_first_teacher_and_subsequent_student(self):self.assertEqual((self.t['role'],self.s['role']),('teacher','student'))
 def test_draft_protected_and_published_visible_without_enrolment(self):
  with self.assertRaises(PermissionError):self.p.course(self.cid,self.s)
  self.p.publish(self.cid,self.t,True);self.assertEqual(len(self.p.listing(self.s)),1)
  with self.assertRaises(PermissionError):self.p.course(self.cid,self.s,True)
 def test_student_cannot_publish(self):
  with self.assertRaises(PermissionError):self.p.publish(self.cid,self.s,True)
 def test_only_consented_active_comments_enter_snapshot(self):
  self.p.publish(self.cid,self.t,True)
  self.p.post_comment(self.cid,self.s,{'text':'为什么？','playback_ms':1000,'analysis':False})
  self.assertEqual(self.p.snapshot(self.cid,self.t)['count'],0)
  with patch('teaching_platform.time.time',return_value=9999999999):self.p.post_comment(self.cid,self.s,{'text':'这里怎么推导？','playback_ms':2000,'analysis':True})
  self.assertEqual(self.p.snapshot(self.cid,self.t)['count'],1)
  r=self.p.comments(self.cid,self.s)[-1];self.p.withdraw(self.cid,self.s,r['id'])
  self.assertEqual(self.p.snapshot(self.cid,self.t)['count'],0)
  self.assertTrue((self.p.assets(self.cid).parent/'analysis/withdrawal.json').exists())
 def test_invalid_timestamps_and_paths_rejected(self):
  for t in (-1, float('nan'),True,61000):
   with self.assertRaises(ValueError):self.p.post_comment(self.cid,self.t,{'text':'问','playback_ms':t})
  with self.assertRaises(ValueError):self.p.assets('../secrets')
 def test_password_not_plaintext_and_logout_revokes(self):
  with self.p.connect() as c:self.assertNotIn('long-password',c.execute('SELECT password FROM users').fetchone()[0])
  raw=self.p.auth({'name':'teacher','password':'long-password'});self.p.logout('course_session='+raw);self.assertIsNone(self.p.user('course_session='+raw))
 def test_remote_snapshot_requires_recipient_specific_consent(self):
  self.p.publish(self.cid,self.t,True)
  self.p.post_comment(self.cid,self.s,{'text':'仅本地分析','playback_ms':1000,'analysis':True})
  with patch('teaching_platform.time.time',return_value=9999999999),patch('teaching_platform.external_service',return_value={'url':'https://example.org/v1','vendor':'test'}):
   self.p.post_comment(self.cid,self.s,{'text':'同意指定服务分析','playback_ms':2000,'analysis':True,'external':True,'external_endpoint':'https://example.org/v1'})
  self.assertEqual(self.p.snapshot(self.cid,self.t)['count'],2)
  self.assertEqual(self.p.snapshot(self.cid,self.t,'https://example.org/v1')['count'],1)
  self.assertEqual(self.p.snapshot(self.cid,self.t,'https://another.example/v1')['count'],0)
 def test_changed_recipient_rejects_stale_consent(self):
  with patch('teaching_platform.external_service',return_value={'url':'https://new.example/v1','vendor':'test'}):
   with self.assertRaises(ValueError):self.p.post_comment(self.cid,self.t,{'text':'问题','playback_ms':1000,'analysis':True,'external':True,'external_endpoint':'https://old.example/v1'})
 def test_visual_boundaries_respect_minimum_gap_and_total_scope(self):
  windows=boundary_candidates([(5,.8),(35,.3),(40,.8),(215,0)],240)
  self.assertEqual([w['start_s'] for w in windows],[0,35,215]);self.assertEqual(windows[-1]['end_s'],240)

if __name__=='__main__':unittest.main()
