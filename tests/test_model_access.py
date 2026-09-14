import unittest
from unittest.mock import patch
import api_settings as api
from model_access import require_ready


class AccessTests(unittest.TestCase):
    def setUp(self):
        api.clear()
        api.configure(dict(vendor='bailian',url='https://dashscope.aliyuncs.com/compatible-mode/v1',key='unit-test-only',model='test-model'))
    def tearDown(self):api.clear()
    def pass_probe(self,vision=False):
        response={'choices':[{'finish_reason':'stop','message':{'content':'{"ok":true}'}}],'usage':{'prompt_tokens':2,'completion_tokens':1}}
        with patch.object(api,'request_json',return_value=response):api.probe(vision)
    def test_saved_key_does_not_open_analysis(self):
        with self.assertRaises(ValueError):require_ready('api','text')
    def test_text_and_vision_permissions_separate(self):
        self.pass_probe()
        require_ready('api','text')
        with self.assertRaises(ValueError):require_ready('api','multimodal')
        self.pass_probe(True)
        require_ready('api','multimodal')
    def test_model_change_revokes_permissions(self):
        self.pass_probe(True)
        api.select_model({'model':'another-model'})
        with self.assertRaises(ValueError):require_ready('api','text')
    def test_failure_revokes_both_permissions(self):
        self.pass_probe(True)
        api.invalidate('连接异常')
        with self.assertRaises(ValueError):require_ready('api','multimodal')
    def test_expiry_requires_new_probe(self):
        self.pass_probe()
        with patch('api_settings.time.time',return_value=api.STATE['text_verified_until']+1):
            with self.assertRaises(ValueError):require_ready('api','text')
    def test_campus_never_opened_by_environment_configuration(self):
        with self.assertRaises(ValueError):require_ready('campus','text')
    def test_local_service_loss_blocks(self):
        with patch('local_model.status',return_value={'connected':False,'model':'test'}):
            with self.assertRaises(ValueError):require_ready('local','text')

if __name__=='__main__':unittest.main()
