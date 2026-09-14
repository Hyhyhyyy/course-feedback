import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from course_feedback.pipeline import read_comments, read_transcript, rule_analysis, build_report, validate_report
from acquire_course import normalize_url


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def write(self,name,data):
        p=self.root/name;p.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');return p
    def test_keep_identical_text_from_different_records(self):
        rows=[{'source_id':'a','playback_ms':1,'text':'不懂'},{'source_id':'b','playback_ms':1,'text':'不懂'},
              {'source_id':'a','playback_ms':1,'text':'不懂'}]
        c,a=read_comments(self.write('c.json',rows),54)
        self.assertEqual(len(c),2);self.assertEqual(a['duplicate_count'],1)
    def test_conflicting_id_is_not_silently_deduplicated(self):
        rows=[{'source_id':'a','playback_ms':1,'text':'不懂'},{'source_id':'a','playback_ms':1,'text':'懂了'}]
        c,a=read_comments(self.write('c.json',rows),54)
        self.assertEqual(a['rejected_count'],1)
    def test_bad_timestamps_and_private_fields(self):
        rows=[{'playback_ms':x,'text':'联系13800138000 或 a@example.com','uid':'private'} for x in (-1,54001,float('nan'),12)]
        c,a=read_comments(self.write('c.json',rows),54)
        self.assertEqual(a['rejected_count'],3);self.assertNotIn('13800138000',c[0]['text']);self.assertNotIn('uid',c[0])
    def test_question_without_question_mark_and_pure_emotion(self):
        self.assertEqual(len(rule_analysis({'id':'a','text':'完全跟不上'})['questions']),1)
        self.assertEqual(rule_analysis({'id':'b','text':'崩溃了'})['questions'],[])
    def test_two_questions_and_positive(self):
        self.assertEqual(len(rule_analysis({'id':'a','text':'为什么？怎么做？'})['questions']),2)
        self.assertTrue(rule_analysis({'id':'b','text':'老师讲得清楚'})['positive'])
    def test_xml_seconds_and_record_id(self):
        p=self.root/'c.xml';p.write_text('<i><d p="1.25,1,25,1,0,0,hash,id1">没懂</d></i>',encoding='utf-8')
        c,a=read_comments(p,54);self.assertEqual(c[0]['playback_ms'],1250)
        p.write_text('<!DOCTYPE i [<!ENTITY x "bad">]><i/>')
        with self.assertRaises(ValueError):read_comments(p,54)
    def test_transcript_adapter_and_invalid_segments(self):
        p=self.write('t.json',{'transcript':{'segments':[{'start':1,'end':2,'text':'导数'}]}})
        self.assertEqual(read_transcript(p,54)[0]['start_ms'],1000)
        p=self.write('t.json',{'segments':[{'start':4,'end':2,'text':'bad'}]})
        with self.assertRaises(ValueError):read_transcript(p,54)
    def test_end_boundary_counts_and_all_question_references(self):
        rows=[{'playback_ms':54000,'text':'为什么？怎么做？'}]
        c,a=read_comments(self.write('c.json',rows),54)
        r=build_report({'duration_s':54},c,a,[],[rule_analysis(x) for x in c],'rules')
        self.assertEqual(r['question_count'],2);self.assertTrue(validate_report(r))
        r['questions'][0]['comment_id']='missing'
        with self.assertRaises(ValueError):validate_report(r)
    def test_course_url_scope(self):
        self.assertEqual(normalize_url('https://www.bilibili.com/video/BV1Y2DGYoEEw/?p=2&spm_id=test'),
                         'https://www.bilibili.com/video/BV1Y2DGYoEEw/?p=2')
        for url in ('http://127.0.0.1/a','https://bilibili.com.attacker.test/video/BV1Y2DGYoEEw/',
                    'https://user:secret@www.bilibili.com/video/BV1Y2DGYoEEw/'):
            with self.assertRaises(ValueError):normalize_url(url)


if __name__=='__main__':unittest.main()
