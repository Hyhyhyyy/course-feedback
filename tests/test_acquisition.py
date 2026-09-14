import gzip
import json
import sys
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fetch_course import decode_body,public_summary
from bilibili_login import BilibiliLogin


class AcquisitionTests(unittest.TestCase):
    def test_xml_transfer_compression(self):
        body='<i><d p="1,1,1,1,1,1,1,id">真实时间格式用例</d></i>'.encode()
        compressor=zlib.compressobj(wbits=-zlib.MAX_WBITS)
        raw=compressor.compress(body)+compressor.flush()
        for encoded,method in ((body,''),(gzip.compress(body),'gzip'),(zlib.compress(body),'deflate'),(raw,'deflate')):
            self.assertEqual(decode_body(encoded,method),body)
        with self.assertRaises(ValueError):decode_body(body,'unknown')
    def test_summary_hides_local_credentials_and_paths(self):
        summary=public_summary({'status':'acquired','media_path':'private-path','cookie_file':'private-cookie','api_key':'secret'})
        self.assertNotIn('private',json.dumps(summary));self.assertNotIn('secret',json.dumps(summary))
    def test_opening_qr_is_not_login_success(self):
        login=BilibiliLogin()
        with patch.object(login,'request',return_value={'code':0,'data':{'url':'https://account.bilibili.com/example','qrcode_key':'test-key'}}):
            result=login.start()
        self.assertFalse(login.status()['logged_in']);self.assertIn('data:image/svg+xml;base64,',result['qr_image'])
        with patch.object(login,'request',side_effect=[{'code':0,'data':{'code':0}},{'code':0,'data':{'isLogin':False}}]):
            self.assertFalse(login.poll()['logged_in'])
    def test_verified_login_and_clear(self):
        login=BilibiliLogin();login.key='test';login.created=__import__('time').monotonic()
        with patch.object(login,'request',side_effect=[{'code':0,'data':{'code':0}},{'code':0,'data':{'isLogin':True}}]):
            self.assertTrue(login.poll()['logged_in'])
        self.assertFalse(login.clear()['logged_in'])
    def test_profile_allowlist_and_expired_session(self):
        login=BilibiliLogin()
        login.accept_nav({'code':0,'data':{'isLogin':True,'uname':'测试账号','mid':123,'level_info':{'current_level':5},'money':99,'cookie':'secret'}})
        self.assertEqual(login.status()['profile'],{'name':'测试账号','uid':'123','level':5})
        self.assertNotIn('secret',json.dumps(login.status()))
        login.last_check=0
        with patch.object(login,'request',return_value={'code':-101}):state=login.refresh()
        self.assertEqual(state['state'],'expired');self.assertIsNone(state['profile'])
        self.assertFalse(state['logged_in'])
    def test_scan_confirmation_and_qr_expiry(self):
        login=BilibiliLogin();login.key='test';login.created=__import__('time').monotonic()
        with patch.object(login,'request',return_value={'code':0,'data':{'code':86090,'message':'请确认'}}):
            self.assertEqual(login.poll()['state'],'waiting_confirm')
        self.assertFalse(login.status()['logged_in'])
        login.created-=181
        self.assertEqual(login.status()['state'],'qr_expired')
        self.assertIsNone(login.key)
    def test_network_error_does_not_claim_expired_or_connected(self):
        login=BilibiliLogin()
        with patch.object(login,'request',side_effect=OSError('network')):state=login.refresh()
        self.assertEqual(state['state'],'verification_failed')
        self.assertFalse(state['logged_in'])


if __name__=='__main__':unittest.main()
