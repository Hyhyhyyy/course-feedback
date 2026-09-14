import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import api_settings as api
from output_contract import validate


class SettingsTests(unittest.TestCase):
    def setUp(self):api.clear()
    def tearDown(self):api.clear()
    def configure(self,**kw):
        return api.configure(dict(vendor='deepseek',url='https://api.deepseek.com',key='test-secret-not-real',model='example',**kw))
    def test_external_self_identification_mask_preserves_evidence_id(self):
        from external_privacy import mask
        result=mask({'id':'c0001','text':'我某大学-专业-张三实名开卷，为什么要求极限？'})
        self.assertEqual(result['id'],'c0001')
        self.assertNotIn('张三',result['text'])
        self.assertIn('为什么要求极限',result['text'])
    def test_secret_not_exposed(self):
        self.configure()
        self.assertNotIn('test-secret-not-real',json.dumps(api.public()))
        self.assertTrue(api.public()['key_present'])
    def test_missing_key_and_insecure_url_rejected(self):
        for url,key in [('http://example.com/v1','x'),('https://example.com/v1','')]:
            with self.assertRaises(ValueError):api.configure(dict(url=url,key=key))
    def test_listing_does_not_claim_inference_permission(self):
        self.configure()
        with patch.object(api,'request_json',return_value={'data':[{'id':'new-model'}]}):
            state=api.models()
        self.assertEqual(state['models'],['new-model'])
        self.assertIn('尚待验证',state['key_status'])
    def test_failed_probe_records_failure(self):
        self.configure()
        with patch.object(api,'request_json',side_effect=ValueError('Key 未通过认证')):
            with self.assertRaises(ValueError):api.probe()
        self.assertIn('未通过',api.public()['key_status'])
    def test_probe_counts_actual_usage(self):
        self.configure()
        response={'choices':[{'finish_reason':'stop','message':{'content':'{"ok":true}'}}],'usage':{'prompt_tokens':12,'completion_tokens':5}}
        with patch.object(api,'request_json',return_value=response):state=api.probe()
        self.assertEqual((state['requests'],state['input_tokens'],state['output_tokens']),(1,12,5))
    def test_missing_usage_not_claimed_zero(self):
        api.record_usage(None)
        self.assertEqual(api.public()['missing_usage'],1)
    def test_bailian_pagination(self):
        api.configure(dict(vendor='bailian',url='https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1',key='test-only'))
        pages=[{'output':{'total':2,'models':[{'model':'a'}]}},{'output':{'total':2,'models':[{'model':'b'}]}}]
        with patch.object(api,'request_json',side_effect=pages) as call:
            self.assertEqual(api.models()['models'],['a','b'])
        self.assertIn('/api/v1/models?page_no=2',call.call_args.args[0])
    def test_schema_rejects_missing_refs_and_boolean_index(self):
        schema={'type':'object','required':['ids'],'properties':{'ids':{'type':'array','minItems':1,'items':{'type':'integer','enum':[0,1]}}},'additionalProperties':False}
        for value in ({},{'ids':[]},{'ids':[True]},{'ids':[2]}):
            with self.assertRaises(ValueError):validate(value,schema)
        validate({'ids':[1]},schema)

if __name__=='__main__':unittest.main()
