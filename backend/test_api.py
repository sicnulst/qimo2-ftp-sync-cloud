"""
功能测试脚本
"""
import requests
import json

BASE_URL = 'http://127.0.0.1:5000/api'
token = None

def test_health():
    """测试健康检查"""
    r = requests.get(f'{BASE_URL}/health')
    print(f'[健康检查] {r.json()}')
    return r.status_code == 200

def test_register():
    """测试注册"""
    global token
    r = requests.post(f'{BASE_URL}/auth/register', json={
        'username': 'testuser',
        'password': 'test123456'
    })
    data = r.json()
    print(f'[注册] {data}')
    if 'access_token' in data:
        token = data['access_token']
    return r.status_code in [200, 201, 409]

def test_login():
    """测试登录"""
    global token
    r = requests.post(f'{BASE_URL}/auth/login', json={
        'username': 'testuser',
        'password': 'test123456'
    })
    data = r.json()
    print(f'[登录] {data}')
    if 'access_token' in data:
        token = data['access_token']
    return r.status_code == 200

def get_headers():
    return {'Authorization': f'Bearer {token}'}

def test_ftp_builtin():
    """测试内置FTP服务器"""
    r = requests.get(f'{BASE_URL}/ftp/builtin/status')
    print(f'[FTP状态] {r.json()}')
    return r.status_code == 200

def test_add_server():
    """测试添加FTP服务器"""
    r = requests.post(f'{BASE_URL}/ftp/servers', json={
        'name': '测试服务器',
        'host': '127.0.0.1',
        'port': 2121,
        'username': 'admin',
        'password': 'admin123',
        'remote_path': '/'
    }, headers=get_headers())
    print(f'[添加服务器] {r.json()}')
    return r.status_code in [200, 201]

def test_list_servers():
    """测试获取服务器列表"""
    r = requests.get(f'{BASE_URL}/ftp/servers', headers=get_headers())
    print(f'[服务器列表] {r.json()}')
    return r.status_code == 200

def test_create_task():
    """测试创建同步任务"""
    r = requests.post(f'{BASE_URL}/sync/tasks', json={
        'ftp_server_id': 1,
        'local_path': '/tmp/test_sync',
        'remote_path': '/',
        'sync_strategy': 'newest',
        'scan_interval': 60,
        'auto_sync': False
    }, headers=get_headers())
    print(f'[创建任务] {r.json()}')
    return r.status_code in [200, 201]

def test_list_tasks():
    """测试获取任务列表"""
    r = requests.get(f'{BASE_URL}/sync/tasks', headers=get_headers())
    print(f'[任务列表] {json.dumps(r.json(), indent=2, ensure_ascii=False)}')
    return r.status_code == 200

def test_history():
    """测试获取历史"""
    r = requests.get(f'{BASE_URL}/history/all', headers=get_headers())
    print(f'[同步历史] {r.json()}')
    return r.status_code == 200

def test_stats():
    """测试获取统计"""
    r = requests.get(f'{BASE_URL}/history/stats', headers=get_headers())
    print(f'[统计信息] {r.json()}')
    return r.status_code == 200

def run_tests():
    """运行所有测试"""
    tests = [
        ('健康检查', test_health),
        ('注册', test_register),
        ('登录', test_login),
        ('FTP状态', test_ftp_builtin),
        ('添加服务器', test_add_server),
        ('服务器列表', test_list_servers),
        ('创建任务', test_create_task),
        ('任务列表', test_list_tasks),
        ('同步历史', test_history),
        ('统计信息', test_stats)
    ]
    
    print('=' * 50)
    print('开始功能测试')
    print('=' * 50)
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f'[通过] {name}')
            else:
                failed += 1
                print(f'[失败] {name}')
        except Exception as e:
            failed += 1
            print(f'[错误] {name}: {e}')
    
    print('=' * 50)
    print(f'测试完成: {passed} 通过, {failed} 失败')
    print('=' * 50)

if __name__ == '__main__':
    import os
    os.makedirs('/tmp/test_sync', exist_ok=True)
    run_tests()
