import base64
import io
import sys
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from syllabus import parse_upload,present_report,PLACEHOLDER


class SyllabusTests(unittest.TestCase):
    def test_text_keeps_teacher_wording(self):
        raw='教学目标\n理解导数定义\n\n例题与适用条件'.encode()
        d=parse_upload({'name':'大纲.txt','content':base64.b64encode(raw).decode()})
        self.assertEqual(d['paragraph_count'],3)
        self.assertEqual(d['paragraphs'][1],{'id':'o0002','text':'理解导数定义'})
    def test_docx_paragraphs(self):
        f=io.BytesIO()
        with zipfile.ZipFile(f,'w') as z:
            z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>目标一</w:t></w:r></w:p></w:body></w:document>')
        d=parse_upload({'name':'大纲.docx','content':base64.b64encode(f.getvalue()).decode()})
        self.assertEqual(d['text'],'目标一')
    def test_invalid_upload_does_not_become_objectives(self):
        for name,raw in [('x.txt',b' '),('x.docx',b'not a zip'),('x.pdf',b'%PDF')]:
            with self.assertRaises(ValueError):parse_upload({'name':name,'content':base64.b64encode(raw).decode()})
    def test_presentation_hides_unvalidated_claims_preserves_observations(self):
        report={'comments':[{'id':'c1','text':'不懂','playback_ms':100,'labels':['问题与求助']}],
                'segments':[{'text':'raw ASR'}],'frames':[{'file':'frame.jpg'}],
                'label_counts':{'问题与求助':1},'timeline':[{'count':1,'question_count':1}]}
        r=present_report(report,{'text':'教师提供的大纲'})
        self.assertEqual(r['media_summary']['transcript_segments'],1)
        self.assertEqual(r['segments'],[]);self.assertIsNone(r['label_counts']['问题与求助'])
        self.assertEqual(r['integrated_evaluation']['outline_alignment'],PLACEHOLDER)
        self.assertEqual(r['comments'][0]['text'],'不懂')
        self.assertEqual(report['label_counts']['问题与求助'],1)
