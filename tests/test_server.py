import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import server


class DemoServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.mkdtemp(prefix='alfa-server-test-')
        cls.original_db = server.DB_FILE
        server.DB_FILE = Path(cls.temp) / 'test.sqlite'

    @classmethod
    def tearDownClass(cls):
        server.DB_FILE = cls.original_db
        shutil.rmtree(cls.temp, ignore_errors=True)

    def test_synthetic_inn_validity(self):
        self.assertTrue(server.inn_is_valid('0000000000'))
        self.assertTrue(server.inn_is_valid('000000000000'))
        self.assertTrue(server.inn_is_valid('782508416860'))
        self.assertFalse(server.inn_is_valid('1234567890'))
        self.assertFalse(server.inn_is_valid('bad'))

    def test_demo_company_fields(self):
        data = server.COMPANIES['0000000000']
        self.assertEqual(data['form']['value'], 'ООО')
        self.assertIn('Синтетический', data['name']['source'])
        self.assertTrue(server.inn_is_valid(data['inn']['value']))

    def test_save_and_list_apps(self):
        obj = {'id':'DEMO-TEST-001', 'profile':{'name':'ООО Тест'}, 'status':'Отправлена', 'history':[]}
        server.upsert_app(obj)
        self.assertEqual(len(server.list_apps()), 1)
        obj['status'] = 'Одобрена'
        server.upsert_app(obj)
        self.assertEqual(len(server.list_apps()), 1)
        self.assertEqual(server.list_apps()[0]['status'], 'Одобрена')

    def test_reject_invalid_payload(self):
        with self.assertRaises(ValueError):
            server.upsert_app({'id':'/bad', 'profile':{}})
        with self.assertRaises(ValueError):
            server.upsert_app({'id':'DEMO', 'profile':'not-an-object'})


if __name__ == '__main__':
    unittest.main()
