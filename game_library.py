"""Small loopback-only editor and encrypted GitHub Pages publisher."""
import argparse
import base64
import datetime
import http.cookies
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / 'スマホ閲覧ページ'
LOCK = threading.RLock()
SESSION = secrets.token_urlsafe(32)
AAD = b'all-game-list:v1'
DEFAULT_PORT = 8767

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))

def write_atomic(path, data):
    text = json.dumps(data,ensure_ascii=False,indent=2)
    fd, name = tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)

def library():
    return read_json(ROOT / 'library.json')

def key_string():
    path = ROOT / 'device-key.json'
    if not path.exists():
        write_atomic(path, {'key':base64.urlsafe_b64encode(AESGCM.generate_key(bit_length=256)).decode().rstrip('=')})
    return read_json(path)['key']

def settings():
    path = ROOT / 'local-settings.json'
    return read_json(path) if path.exists() else {'remote':'','branch':'main','pageUrl':''}

def editor_template():
    return (ROOT / 'app.html').read_text(encoding='utf-8').replace('/*LOCAL_MODE*/false','true')

def export_viewer():
    data = library()
    key = base64.urlsafe_b64decode(key_string()+'=')
    template = (ROOT / 'app.html').read_text(encoding='utf-8')
    if (PUBLIC/'index.html').exists() and (PUBLIC/'library.enc.json').exists():
        try:
            previous = read_json(PUBLIC/'library.enc.json')
            decoded = AESGCM(key).decrypt(base64.b64decode(previous['iv']),
                                           base64.b64decode(previous['ciphertext']), AAD)
            if json.loads(decoded) == data and (PUBLIC/'index.html').read_text(encoding='utf-8') == template:
                return data
        except (ValueError, KeyError, TypeError, OSError, InvalidTag):
            pass  # An invalid old export is replaced from the local saved library.
    iv = secrets.token_bytes(12)
    encrypted = AESGCM(key).encrypt(iv,json.dumps(data,ensure_ascii=False).encode(),AAD)
    PUBLIC.mkdir(exist_ok=True)
    (PUBLIC / 'index.html').write_text(template,encoding='utf-8')
    write_atomic(PUBLIC / 'library.enc.json', {'schemaVersion':1,'algorithm':'AES-256-GCM',
                 'iv':base64.b64encode(iv).decode(),'ciphertext':base64.b64encode(encrypted).decode()})
    return data

def run_git(*args, check=True):
    result = subprocess.run(['git',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',
                            errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=90)
    if check and result.returncode:
        raise RuntimeError('GitHubへの反映に失敗しました。PCの保存内容は残っています。認証・接続を確認して再試行してください。')
    return result

def publish():
    with LOCK:
        data = export_viewer()
        cfg = settings()
        if not cfg.get('remote'):
            return {'published':False,'message':'閲覧用ページを作成しました。GitHubの公開先はまだ設定されていません。','revision':data['revision']}
        # Do not commit unrelated staged work. Only the ciphertext and viewer are published here.
        staged = run_git('diff','--cached','--name-only').stdout.strip()
        if staged:
            raise RuntimeError('別の変更がGitのステージにあります。公開処理を中止しました。PCの保存内容は残っています。')
        run_git('status','--short')
        run_git('diff','--stat')
        run_git('add','--','スマホ閲覧ページ/index.html','スマホ閲覧ページ/library.enc.json')
        changed = run_git('diff','--cached','--quiet',check=False).returncode
        if changed:
            run_git('commit','-m',f'Update encrypted game list (revision {data["revision"]})')
        run_git('push',cfg['remote'],cfg['branch'])
        status = run_git('status','--short').stdout.strip()
        local = run_git('rev-parse','HEAD').stdout.strip()
        remote = run_git('ls-remote',cfg['remote'],f'refs/heads/{cfg["branch"]}').stdout.split()
        if not remote or remote[0] != local:
            raise RuntimeError('GitHubとの同期を確認できませんでした。再試行してください。')
        cfg['publishedRevision'] = data['revision']
        cfg['publishedAt'] = now()
        write_atomic(ROOT/'local-settings.json',cfg)
        return {'published':True,'revision':data['revision'],'commit':local[:7],
                'message':'GitHubへの送信が完了しました。スマホ側への反映には少し時間がかかります。'}

def update_record(payload):
    with LOCK:
        data = library()
        if payload.get('revision') != data['revision']:
            raise ValueError('別の画面で更新されています。再読み込みしてから変更してください。')
        game = next((g for g in data['games'] if g['id'] == payload.get('id')),None)
        if game is None: raise ValueError('ゲームが見つかりません。')
        change = payload.get('changes')
        if not isinstance(change,dict) or not change or set(change)-{'interest','owned','wanted','memo'}:
            raise ValueError('変更項目が不正です。')
        if 'interest' in change and change['interest'] not in ('unknown','curious','play','none'):
            raise ValueError('興味の値が不正です。')
        if 'owned' in change and change['owned'] not in ('unknown','yes','no'):
            raise ValueError('所有の値が不正です。')
        if 'wanted' in change and type(change['wanted']) is not bool:
            raise ValueError('探し中の値が不正です。')
        if 'memo' in change and (not isinstance(change['memo'],str) or len(change['memo']) > 4000):
            raise ValueError('メモは4000文字以内で入力してください。')
        shutil.copy2(ROOT/'library.json',ROOT/'library.previous.json')
        game.update(change)
        data['revision'] += 1
        data['updatedAt'] = now()
        write_atomic(ROOT/'library.json',data)
        return data

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass  # never log private URLs, query strings or records

    def host_valid(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')

    def session_valid(self):
        try:
            cookies = http.cookies.SimpleCookie(self.headers.get('Cookie',''))
            return secrets.compare_digest(cookies['agl-session'].value,SESSION)
        except (KeyError,http.cookies.CookieError):
            return False

    def send_bytes(self,content,ctype='application/json; charset=utf-8',status=200,cookie=False):
        self.send_response(status)
        self.send_header('Content-Type',ctype)
        self.send_header('Content-Length',str(len(content)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Frame-Options','DENY')
        if cookie:
            self.send_header('Set-Cookie',f'agl-session={SESSION}; HttpOnly; SameSite=Strict; Path=/')
        self.end_headers()
        self.wfile.write(content)

    def json_response(self,obj,status=200):
        self.send_bytes(json.dumps(obj,ensure_ascii=False).encode(),'application/json; charset=utf-8',status)

    def do_GET(self):
        if not self.host_valid(): return self.json_response({'error':'Host is not allowed'},403)
        path = urllib.parse.urlsplit(self.path).path
        if path == '/':
            return self.send_bytes(editor_template().encode(),'text/html; charset=utf-8',cookie=True)
        if path == '/health': return self.json_response({'app':'all-game-list','version':1})
        if path in ('/viewer/','/viewer/index.html','/viewer/library.enc.json'):
            f = PUBLIC / ('library.enc.json' if path.endswith('.json') else 'index.html')
            if not f.exists(): return self.json_response({'error':'閲覧用ページが未作成です。'},404)
            return self.send_bytes(f.read_bytes(),'application/json; charset=utf-8' if f.suffix=='.json' else 'text/html; charset=utf-8')
        if path.startswith('/api/') and not self.session_valid():
            return self.json_response({'error':'PC画面を開き直してください。'},403)
        if path == '/api/library': return self.json_response(library())
        if path == '/api/info':
            cfg = settings()
            return self.json_response({'publishedRevision':cfg.get('publishedRevision',-1),'pageConfigured':bool(cfg.get('pageUrl'))})
        if path == '/api/links':
            cfg = settings()
            suffix = '#k='+key_string()
            return self.json_response({'preview':'/viewer/'+suffix,'public':cfg.get('pageUrl','')+suffix if cfg.get('pageUrl') else ''})
        if path == '/api/backup':
            return self.json_response(library())
        return self.json_response({'error':'見つかりません。'},404)

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length','0'))
        except ValueError:
            return self.json_response({'error':'リクエストの大きさが不正です。'},400)
        if not 0 < length <= 25000:
            return self.json_response({'error':'リクエストの大きさが不正です。'},400)
        raw = self.rfile.read(length)
        if not self.host_valid() or not self.session_valid():
            return self.json_response({'error':'PC画面を開き直してください。'},403)
        origin = self.headers.get('Origin','')
        if origin != f'http://{self.headers.get("Host")}':
            return self.json_response({'error':'外部の画面からは変更できません。'},403)
        try:
            payload = json.loads(raw)
            if not isinstance(payload,dict): raise ValueError('データ形式が不正です。')
            if self.path == '/api/update': return self.json_response(update_record(payload))
            if self.path == '/api/export':
                with LOCK: data = export_viewer()
                return self.json_response({'revision':data['revision']})
            if self.path == '/api/publish': return self.json_response(publish())
            return self.json_response({'error':'見つかりません。'},404)
        except (ValueError, RuntimeError) as exc:
            return self.json_response({'error':str(exc)},400)
        except Exception:
            return self.json_response({'error':'処理を完了できませんでした。PCの保存済みデータは残っています。接続とGitHub認証を確認して再試行してください。'},500)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--open',action='store_true')
    parser.add_argument('--export',action='store_true')
    parser.add_argument('--port',type=int,default=DEFAULT_PORT)
    args = parser.parse_args()
    if args.export:
        export_viewer()
        print('Encrypted viewer exported.')
        return
    if not (ROOT/'library.json').exists():
        from import_neogeo import import_library
        import_library()
    if not (PUBLIC/'index.html').exists() or not (PUBLIC/'library.enc.json').exists():
        export_viewer()
    try:
        server = ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    except OSError:
        import urllib.request
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{args.port}/health',timeout=2) as response:
                if json.load(response).get('app') != 'all-game-list': raise RuntimeError()
        except Exception:
            raise SystemExit('Port is in use by another application.')
        if args.open: webbrowser.open(f'http://127.0.0.1:{args.port}/')
        return
    if args.open: webbrowser.open(f'http://127.0.0.1:{args.port}/')
    server.serve_forever()

if __name__ == '__main__': main()
