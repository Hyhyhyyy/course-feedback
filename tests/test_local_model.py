import unittest
from local_model import cited_items, classify, screen_review
from course_feedback.pipeline import LABELS
from syllabus import present_report


class FakeClient:
    def __init__(self, result): self.result=result; self.calls=0
    def ask(self, *args, **kwargs): self.calls+=1; return self.result


class LocalModelTests(unittest.TestCase):
    def test_unsupported_mastery_and_population_claims_screened(self):
        answer={'overview':'学生普遍掌握不足','findings':[{'text':'学生掌握不足','evidence_ids':['c1']},{'text':'反馈提出为何取极限；候选行动：补充实例','evidence_ids':['c1']}],'alignment':[]}
        safe,n=screen_review(answer)
        self.assertEqual(n,2)
        self.assertEqual(len(safe['findings']),1)
        self.assertEqual(len(answer['findings']),2)

    def test_invalid_citations_rejected(self):
        for refs in [[], ['missing'], 'c1']:
            with self.assertRaises(ValueError):
                cited_items([{'text':'建议','evidence_ids':refs}], {'c1'})
        self.assertEqual(len(cited_items([{'text':'建议','evidence_ids':['c1']}], {'c1'})),1)

    def test_duplicates_keep_separate_timestamps(self):
        client=FakeClient({k:([0] if k=='理解自述' else []) for k in LABELS+['积极表达','语义不明','无关']})
        comments=[{'id':'c1','text':'没懂','playback_ms':1}, {'id':'c2','text':'没懂','playback_ms':900}]
        output=classify(comments,client,lambda **kwargs:None)
        self.assertEqual([x['id'] for x in output],['c1','c2'])
        self.assertTrue(all(x['questions'] for x in output))
        self.assertEqual(client.calls,1)

    def test_missing_model_rows_rejected(self):
        with self.assertRaises(ValueError):
            classify([{'id':'c1','text':'示例','playback_ms':1}],FakeClient({'items':[]}),lambda **kwargs:None)

    def test_explicit_unresolved_record_is_retained(self):
        client=FakeClient({k:[] for k in LABELS+['积极表达','语义不明','无关']})
        output=classify([{'id':'c1','text':'???','playback_ms':1}],client,lambda **kwargs:None)
        self.assertTrue(output[0]['model_unresolved'])
        self.assertTrue(output[0]['questions'])
        self.assertEqual(output[0]['id'],'c1')

    def test_changed_outline_hides_old_alignment(self):
        report={'analysis_status':'model_preliminary','syllabus_sha256':'old','model_review':{'alignment':[{'text':'旧对应'}]},'segments':[],'frames':[]}
        result=present_report(report,{'sha256':'new'})
        self.assertTrue(result['syllabus_stale'])
        self.assertEqual(result['model_review']['alignment'],[])
        self.assertEqual(len(report['model_review']['alignment']),1)


if __name__=='__main__': unittest.main()
