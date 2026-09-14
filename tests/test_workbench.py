import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from workbench import run_analysis, analysis_status, read_json, export_html
from fetch_course import save_json
from course_feedback.pipeline import validate_report,rule_analysis


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.assets=self.root/'job/assets';self.assets.mkdir(parents=True)
        save_json(self.assets/'acquisition.json',{'title':'测试课程','duration_s':60,'artifacts':{},'source_url':'https://www.bilibili.com/video/BV1Y2DGYoEEw/'})
        (self.assets/'course.danmaku.xml').write_text('<i><d p="5">为什么这样？</d><d p="10">讲得好，谢谢</d><d p="15">崩溃</d></i>',encoding='utf-8')
    def tearDown(self):self.temp.cleanup()
    def test_text_report_preserves_evidence_without_inventing_transcript(self):
        run_analysis(self.root,self.assets,'text')
        r=read_json(self.root/'job/analysis/report.json')
        self.assertTrue(validate_report(r));self.assertEqual(len(r['comments']),3)
        self.assertEqual(r['segments'],[]);self.assertEqual(r['question_count'],1)
        self.assertEqual(r['summary']['emotion_only'],1)
        self.assertEqual(r['summary']['positive_comments'],1)
    def test_failed_run_cannot_be_reported_as_previous_success(self):
        run_analysis(self.root,self.assets,'text');run_analysis(self.root,self.assets,'multimodal')
        self.assertEqual(analysis_status(self.assets)['status'],'failed')
    def test_imported_transcript_association(self):
        out=self.root/'job/analysis';out.mkdir()
        save_json(out/'imported-transcript.json',{'transcript':{'segments':[{'start':0,'end':20,'text':'这段讲解定义'}]}})
        run_analysis(self.root,self.assets,'imported')
        r=read_json(out/'report.json');self.assertEqual(len(r['segments']),1)
        self.assertEqual(r['questions'][0]['candidate_segment_ids'],['s000001'])
    def test_export_escapes_script_text_and_includes_review(self):
        run_analysis(self.root,self.assets,'text');r=read_json(self.root/'job/analysis/report.json')
        r['course']['title']='</script><script>alert(1)</script>';r['teacher_review']={'notes':'测试复核'}
        actual=Path(__file__).resolve().parents[1]
        output=export_html(actual,r)
        self.assertNotIn('</script><script>alert(1)',output)
        self.assertIn('测试复核',output);self.assertNotIn('__REPORT_DATA__',output)
    def test_negation_and_repeated_question_marks(self):
        for text in ['完了 听不懂了','没有听懂','大家都听懂了吗？','点点举报谢谢喵']:
            self.assertFalse(rule_analysis({'id':'c1','text':text})['positive'],text)
        self.assertTrue(rule_analysis({'id':'c1','text':'没懂公式，但老师图解讲得好'})['positive'])
        result=rule_analysis({'id':'c1','text':'为什么？？？怎么做？'})
        self.assertEqual(len(result['questions']),2)
        self.assertEqual(result['questions'][0]['text'],'为什么？？？')


if __name__=='__main__':unittest.main()
