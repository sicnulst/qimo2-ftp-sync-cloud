# -*- coding: utf-8 -*-
import urllib.request
import urllib.parse
import json
import os
import time
import ssl

ssl._create_default_https_context = ssl._create_unverified_context
BASE = 'http://10.27.82.246:5000/api'
PASS = 0
FAIL = 0
ERRORS = []

def api(method, path, data=None, headers=None, timeout=30):
    url = BASE + path
    body = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header('Content-Type', 'application/json')
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.getcode(), json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode('utf-8'))
        except:
            return e.code, {'error': str(e)}
    except Exception as e:
        return 0, {'error': str(e)}

def log(ok, msg, detail=''):
    global PASS, FAIL, ERRORS
    if ok:
        PASS += 1
        print('[OK]  ' + msg)
    else:
        FAIL += 1
        ERRORS.append(msg + ': ' + detail)
        print('[FAIL] ' + msg + '  >>> ' + detail)

SYNC_DIR = r'C:\temp\ftp_sync_test'
os.makedirs(SYNC_DIR, exist_ok=True)
with open(os.path.join(SYNC_DIR, 'hello.txt'), 'w') as f:
    f.write('Hello FTP sync test!')
os.makedirs(os.path.join(SYNC_DIR, 'sub'), exist_ok=True)
with open(os.path.join(SYNC_DIR, 'sub', 'nested.txt'), 'w') as f:
    f.write('nested content')

# 1. health
print('\n=== 1. health ===')
code, d = api('GET', '/health')
log(code == 200, 'health', str(code))

# 2. register + login
print('\n=== 2. auth ===')
code, d = api('POST', '/auth/register', {'username': 'e2e', 'password': 'test123456'})
log(code in [200, 201, 409], 'register', str(code))

code, d = api('POST', '/auth/login', {'username': 'e2e', 'password': 'test123456'})
token = d.get('access_token')
log(code == 200 and token, 'login', str(code))
H = {'Authorization': 'Bearer ' + (token or '')}

code, d = api('GET', '/auth/profile', headers=H)
log(code == 200, 'profile', str(code))

# 3. FTP server
print('\n=== 3. FTP server ===')
code, d = api('GET', '/ftp/builtin/status')
log(code == 200, 'ftp status', 'running=' + str(d.get('is_running')))

code, d = api('POST', '/ftp/servers', {'name': 'E2E', 'host': '127.0.0.1', 'port': 2121, 'username': 'admin', 'password': 'admin123', 'remote_path': '/e2e'}, headers=H)
sid = d.get('server', {}).get('id')
log(code in [200, 201], 'add server', 'id=' + str(sid))

code, d = api('POST', '/ftp/servers/' + str(sid) + '/test', headers=H)
log(d.get('status') == 'success', 'test connection', d.get('message', str(d)))

code, d = api('GET', '/ftp/servers/' + str(sid) + '/files?path=/', headers=H)
log(code == 200 and 'files' in d, 'list remote files', str(code))

# 4. sync task
print('\n=== 4. sync task ===')
code, d = api('POST', '/sync/tasks', {
    'ftp_server_id': sid, 'local_path': SYNC_DIR,
    'remote_path': '/e2e', 'sync_strategy': 'newest',
    'scan_interval': 60, 'auto_sync': False
}, headers=H)
tid = d.get('task', {}).get('id')
log(code in [200, 201], 'create task', 'task_id=' + str(tid))

code, d = api('GET', '/sync/tasks', headers=H)
log(code == 200 and len(d.get('tasks', [])) > 0, 'task list', str(len(d.get('tasks', []))))

# 5. ignore rules
print('\n=== 5. ignore rules ===')
for p in ['*.tmp', '*.svn', '~$*']:
    code, d = api('POST', '/sync/tasks/' + str(tid) + '/ignore', {'pattern': p}, headers=H)
    log(code in [200, 201], 'add ignore ' + p, str(code))

code, d = api('GET', '/sync/tasks/' + str(tid) + '/ignore', headers=H)
log(code == 200 and len(d.get('rules', [])) >= 3, 'ignore rules', str(len(d.get('rules', []))))

# 6. MANUAL SYNC - the key test
print('\n=== 6. MANUAL SYNC (key test!) ===')
code, d = api('POST', '/sync/tasks/' + str(tid) + '/sync', headers=H, timeout=60)
results = d.get('results', [])
ok_files = [r for r in results if r.get('status') == 'success']
fail_files = [r for r in results if r.get('status') == 'error']
for r in ok_files:
    log(True, 'sync ' + str(r.get('file', '')), r.get('direction','') + ' ' + r.get('action',''))
for r in fail_files:
    log(False, 'sync ' + str(r.get('file', '')), str(r.get('error', '')))
if not results:
    log(False, 'sync result', 'no results')

# verify remote files exist
code, d = api('GET', '/ftp/servers/' + str(sid) + '/files?path=/e2e', headers=H)
rfiles = d.get('files', [])
log(len(rfiles) > 0, 'remote files exist', 'count=' + str(len(rfiles)) + ' names=' + str([f.get('name') for f in rfiles]))

# 7. start/pause task
print('\n=== 7. start/pause ===')
code, d = api('POST', '/sync/tasks/' + str(tid) + '/start', headers=H)
log(code == 200, 'start task', str(code))

with open(os.path.join(SYNC_DIR, 'auto.txt'), 'w') as f:
    f.write('auto sync test')
print('  waiting 12s for auto sync...')
time.sleep(12)

code, d = api('POST', '/sync/tasks/' + str(tid) + '/pause', headers=H)
log(code == 200, 'pause task', str(code))

# 8. history
print('\n=== 8. history ===')
code, d = api('GET', '/history/all', headers=H)
log(code == 200 and 'history' in d, 'history', 'total=' + str(d.get('total', 0)))

code, d = api('GET', '/history/stats', headers=H)
log(code == 200, 'stats', json.dumps(d, ensure_ascii=False))

# 9. watcher/scheduler
print('\n=== 9. watcher/scheduler ===')
code, d = api('GET', '/sync/watcher/status', headers=H)
log(code == 200, 'watcher', str(d))

code, d = api('GET', '/sync/scheduler/status', headers=H)
log(code == 200, 'scheduler', str(d))

# 10. file browser
print('\n=== 10. file browser ===')
code, d = api('GET', '/files/local?path=' + urllib.parse.quote(r'C:\temp') + '&subpath=/ftp_sync_test', headers=H)
log(code == 200 and 'files' in d, 'local files', str(len(d.get('files', []))))

# 11. cleanup
print('\n=== 11. cleanup ===')
code, d = api('DELETE', '/sync/tasks/' + str(tid), headers=H)
log(code == 200, 'delete task', str(code))
code, d = api('DELETE', '/ftp/servers/' + str(sid), headers=H)
log(code == 200, 'delete server', str(code))

# summary
print('\n' + '=' * 50)
print('PASS: ' + str(PASS) + '  FAIL: ' + str(FAIL) + '  TOTAL: ' + str(PASS + FAIL))
if ERRORS:
    print('\nFAILURES:')
    for e in ERRORS:
        print('  - ' + e)
print('=' * 50)
