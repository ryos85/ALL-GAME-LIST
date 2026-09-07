"""Storage, API isolation and encryption checks using disposable data only."""
import base64
import copy
import http.client
import json
import shutil
import secrets
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import game_library as app

REAL_ROOT = Path(__file__).resolve().parent

class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = (REAL_ROOT/('保存動作検証-'+secrets.token_hex(6))).resolve()
        self.temp.mkdir()
        self.assertTrue(self.temp.is_relative_to(REAL_ROOT))
        self.patches = [patch.object(app,'ROOT',self.temp),patch.object(app,'PUBLIC',self.temp/'スマホ閲覧ページ')]
        for p in self.patches: p.start()
        shutil.copy2(REAL_ROOT/'app.html',self.temp/'app.html')
        shutil.copy2(REAL_ROOT/'library.json',self.temp/'library.json')
        self.initial = app.library()

    def tearDown(self):
        for p in self.patches: p.stop()
        self.assertTrue(self.temp.is_relative_to(REAL_ROOT))
        shutil.rmtree(self.temp)

    def test_import_preserves_rows_and_initial_states(self):
        import openpyxl
        book = openpyxl.load_workbook(r'D:\EmuGame\ROMリスト.xlsx',read_only=True,data_only=True)
        original = [row for row in book['ネオジオポケット'].iter_rows(min_row=2,values_only=True) if row[6]]
        book.close()
        games=self.initial['games']
        self.assertEqual(len(games),82)
        self.assertEqual(len({g['id'] for g in games}),82)
        for g,row in zip(games,original):
            self.assertEqual(g['title'],row[6])
            self.assertEqual(g['legacy'],{'owned':row[1] or '', 'rating':row[2] or '', 'want':row[3] or ''})
        self.assertEqual(sum(g['platform']=='NGP' for g in games),9)
        self.assertEqual(sum(g['platform']=='NGPC' for g in games),73)
        self.assertEqual(sum(g['compatibility']=='unknown' for g in games),11)

    def test_update_retains_metadata_and_backups(self):
        old=copy.deepcopy(self.initial)
        updated=app.update_record({'id':'ngp-001','revision':old['revision'],
                                   'changes':{'interest':'play','owned':'no','wanted':True,'memo':'箱・説明書ありを探す <タグ>'}})
        self.assertEqual(app.library(),updated)
        self.assertEqual(app.read_json(self.temp/'library.previous.json'),old)
        self.assertEqual(updated['games'][0]['legacy'],old['games'][0]['legacy'])
        self.assertEqual(updated['games'][0]['memo'],'箱・説明書ありを探す <タグ>')
        self.assertEqual(updated['games'][1:],old['games'][1:])
        self.assertEqual(updated['revision'],old['revision']+1)

    def test_stale_revision_is_rejected_without_overwrite(self):
        app.update_record({'id':'ngp-001','revision':self.initial['revision'],'changes':{'wanted':True}})
        before=(self.temp/'library.json').read_bytes()
        with self.assertRaises(ValueError):
            app.update_record({'id':'ngp-002','revision':self.initial['revision'],'changes':{'wanted':True}})
        self.assertEqual(before,(self.temp/'library.json').read_bytes())

    def test_invalid_updates_do_not_modify_data(self):
        for changes in ({'title':'overwrite'},{'wanted':'yes'},{'owned':'invalid'},{'interest':'invalid'},{'memo':1}):
            with self.assertRaises(ValueError):
                app.update_record({'id':'ngp-001','revision':self.initial['revision'],'changes':changes})
            self.assertEqual(app.library(),self.initial)

    def test_encryption_roundtrip_and_wrong_key_and_tampering(self):
        app.export_viewer()
        envelope=app.read_json(app.PUBLIC/'library.enc.json')
        iv=base64.b64decode(envelope['iv']); cipher=base64.b64decode(envelope['ciphertext'])
        key=base64.urlsafe_b64decode(app.key_string()+'=')
        decoded=AESGCM(key).decrypt(iv,cipher,app.AAD)
        self.assertEqual(json.loads(decoded),self.initial)
        with self.assertRaises(InvalidTag): AESGCM(AESGCM.generate_key(bit_length=256)).decrypt(iv,cipher,app.AAD)
        with self.assertRaises(InvalidTag): AESGCM(key).decrypt(iv,cipher[:-1]+bytes([cipher[-1]^1]),app.AAD)
        public_text=''.join(f.read_text(encoding='utf-8') for f in app.PUBLIC.iterdir())
        self.assertNotIn(self.initial['games'][0]['title'],public_text)
        self.assertNotIn(app.key_string(),public_text)
        first_iv=envelope['iv']
        app.export_viewer()
        self.assertNotEqual(first_iv,app.read_json(app.PUBLIC/'library.enc.json')['iv'])

    def test_http_access_controls_and_update(self):
        server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        port=server.server_port
        def req(method,path,body=None,headers=None):
            conn=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
            conn.request(method,path,body=json.dumps(body) if body is not None else None,headers=headers or {})
            r=conn.getresponse(); out=(r.status,dict(r.getheaders()),r.read());conn.close();return out
        try:
            self.assertEqual(req('GET','/api/library')[0],403)
            first=req('GET','/');self.assertEqual(first[0],200)
            cookie=first[1]['Set-Cookie'].split(';')[0]
            headers={'Cookie':cookie,'Origin':f'http://127.0.0.1:{port}','Content-Type':'application/json'}
            self.assertEqual(req('GET','/api/library',headers={'Cookie':cookie})[0],200)
            for path in ('/library.json','/device-key.json','/../library.json','/.git/config'):
                self.assertEqual(req('GET',path)[0],404)
            self.assertEqual(req('GET','/',headers={'Host':'attacker.example'})[0],403)
            payload={'id':'ngp-001','revision':self.initial['revision'],'changes':{'wanted':True}}
            self.assertEqual(req('POST','/api/update',payload,{**headers,'Origin':'https://attacker.example'})[0],403)
            self.assertEqual(req('POST','/api/update',payload,headers)[0],200)
            self.assertTrue(app.library()['games'][0]['wanted'])
        finally:
            server.shutdown();server.server_close();thread.join()

if __name__=='__main__': unittest.main(verbosity=2)
