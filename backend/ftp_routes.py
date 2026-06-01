"""
FTP服务器管理API
支持多FTP服务器配置、连接池、状态查询
单例模式：FTP连接池管理
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import get_db
from ftp_server import ftp_manager
from ftplib import FTP
import threading

ftp_bp = Blueprint('ftp', __name__)


class FTPConnectionPool:
    """FTP连接池（单例模式）"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.connections = {}
            return cls._instance
    
    def get_connection(self, server_config):
        """获取FTP连接"""
        key = f"{server_config['host']}:{server_config['port']}"
        
        if key in self.connections:
            try:
                ftp = self.connections[key]
                ftp.voidcmd('NOOP')
                return ftp
            except:
                del self.connections[key]
        
        ftp = FTP()
        ftp.connect(server_config['host'], server_config['port'])
        if server_config.get('username'):
            ftp.login(server_config['username'], server_config.get('password', ''))
        else:
            ftp.login()
        ftp.set_pasv(True)
        
        self.connections[key] = ftp
        return ftp
    
    def remove_connection(self, host, port):
        """移除连接"""
        key = f"{host}:{port}"
        if key in self.connections:
            try:
                self.connections[key].quit()
            except:
                pass
            del self.connections[key]
    
    def close_all(self):
        """关闭所有连接"""
        for key, ftp in self.connections.items():
            try:
                ftp.quit()
            except:
                pass
        self.connections.clear()


# 连接池单例
connection_pool = FTPConnectionPool()


@ftp_bp.route('/servers', methods=['GET'])
@jwt_required()
def list_servers():
    """获取FTP服务器列表"""
    user_id = get_jwt_identity()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ftp_servers WHERE user_id = ?', (user_id,))
    servers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'servers': servers})


@ftp_bp.route('/servers', methods=['POST'])
@jwt_required()
def add_server():
    """添加FTP服务器"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    name = data.get('name', '').strip()
    host = data.get('host', '127.0.0.1').strip()
    port = data.get('port', 2121)
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    remote_path = data.get('remote_path', '/').strip()
    
    if not name:
        return jsonify({'error': '服务器名称不能为空'}), 400
    
    # 自动生成隔离的远程目录（防止多个云盘共享同一FTP根目录）
    if remote_path == '/':
        safe_name = name.replace(' ', '_').replace('/', '_')
        remote_path = f'/user_{user_id}/{safe_name}'
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ftp_servers (user_id, name, host, port, username, password, remote_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, name, host, port, username, password, remote_path))
    conn.commit()
    server_id = cursor.lastrowid
    conn.close()
    
    # 尝试在FTP服务器上创建隔离目录
    try:
        ftp = FTP()
        ftp.connect(host, int(port), timeout=5)
        if username:
            ftp.login(username, password)
        else:
            ftp.login()
        ftp.set_pasv(True)
        # 递归创建目录
        parts = remote_path.strip('/').split('/')
        current = ''
        for part in parts:
            current += f'/{part}'
            try:
                ftp.mkd(current)
            except:
                pass
        ftp.quit()
    except Exception as e:
        print(f"[FTP] 创建隔离目录失败（不影响添加）: {e}")
    
    return jsonify({
        'message': '添加成功',
        'server': {
            'id': server_id,
            'name': name,
            'host': host,
            'port': port,
            'remote_path': remote_path
        }
    }), 201


@ftp_bp.route('/servers/<int:server_id>', methods=['DELETE'])
@jwt_required()
def delete_server(server_id):
    """删除FTP服务器及其关联数据和文件"""
    import shutil
    import os
    
    user_id = get_jwt_identity()
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. 先查出服务器信息，获取 remote_path
    cursor.execute('SELECT id, remote_path FROM ftp_servers WHERE id = ? AND user_id = ?', (server_id, user_id))
    server = cursor.fetchone()
    if not server:
        conn.close()
        return jsonify({'error': '服务器不存在'}), 404
    
    remote_path = server['remote_path']
    
    # 2. 查出该服务器下所有同步任务 ID
    cursor.execute('SELECT id FROM sync_tasks WHERE ftp_server_id = ?', (server_id,))
    task_ids = [row['id'] for row in cursor.fetchall()]
    
    # 3. 删除同步历史（无级联，需手动删）
    if task_ids:
        placeholders = ','.join('?' * len(task_ids))
        cursor.execute(f'DELETE FROM sync_history WHERE sync_task_id IN ({placeholders})', task_ids)
    
    # 4. 删除同步任务（ignore_rules 和 sync_snapshots 有 ON DELETE CASCADE，会自动清理）
    cursor.execute('DELETE FROM sync_tasks WHERE ftp_server_id = ?', (server_id,))
    
    # 5. 删除服务器记录
    cursor.execute('DELETE FROM ftp_servers WHERE id = ?', (server_id,))
    conn.commit()
    conn.close()
    
    # 6. 删除 FTP 存储目录（remote_path 格式如 /user_2/yun2）
    if remote_path and remote_path != '/':
        # FTP 根目录下的相对路径
        storage_dir = os.path.join(os.path.dirname(__file__), 'ftp_storage', remote_path.lstrip('/'))
        if os.path.exists(storage_dir):
            try:
                shutil.rmtree(storage_dir)
            except OSError:
                pass  # 目录被占用等，忽略
    
    return jsonify({'message': '删除成功'})


@ftp_bp.route('/servers/<int:server_id>/test', methods=['POST'])
@jwt_required()
def test_connection(server_id):
    """测试FTP连接"""
    user_id = get_jwt_identity()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ftp_servers WHERE id = ? AND user_id = ?', (server_id, user_id))
    server = cursor.fetchone()
    conn.close()
    
    if not server:
        return jsonify({'error': '服务器不存在'}), 404
    
    try:
        ftp = FTP()
        ftp.connect(server['host'], server['port'], timeout=5)
        if server['username']:
            ftp.login(server['username'], server['password'])
        else:
            ftp.login()
        ftp.set_pasv(True)
        
        # 进入该服务器的目录再列文件
        server_path = f'/user_{user_id}/{server["name"]}'
        try:
            ftp.cwd(server_path)
        except:
            # 目录不存在则创建
            try:
                ftp.mkd(server_path)
                ftp.cwd(server_path)
            except:
                pass
        
        # 获取目录列表
        items = []
        try:
            ftp.retrlines('LIST', items.append)
        except:
            pass
        
        ftp.quit()
        
        return jsonify({
            'status': 'success',
            'message': '连接成功',
            'files_count': len(items)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'连接失败: {str(e)}'
        }), 400


@ftp_bp.route('/servers/<int:server_id>/files', methods=['GET'])
@jwt_required()
def list_remote_files(server_id):
    """列出服务器文件"""
    user_id = get_jwt_identity()
    path = request.args.get('path', '/')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ftp_servers WHERE id = ? AND user_id = ?', (server_id, user_id))
    server = cursor.fetchone()
    conn.close()
    
    if not server:
        return jsonify({'error': '服务器不存在'}), 404
    
    try:
        ftp = FTP()
        ftp.connect(server['host'], server['port'], timeout=5)
        if server['username']:
            ftp.login(server['username'], server['password'])
        else:
            ftp.login()
        ftp.set_pasv(True)
        
        ftp.cwd(path)
        
        files = []
        ftp.retrlines('LIST', lambda line: files.append(parse_ftp_list(line, path)))
        
        ftp.quit()
        
        return jsonify({'path': path, 'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


def parse_ftp_list(line, current_path):
    """解析FTP LIST输出"""
    parts = line.split(None, 8)
    if len(parts) < 9:
        return None
    
    is_dir = parts[0].startswith('d')
    size = int(parts[4]) if not is_dir else 0
    name = parts[8]
    
    return {
        'name': name,
        'is_dir': is_dir,
        'size': size,
        'path': f"{current_path.rstrip('/')}/{name}"
    }


@ftp_bp.route('/builtin/status', methods=['GET'])
def builtin_ftp_status():
    """获取内置FTP服务器状态"""
    return jsonify(ftp_manager.get_status())


@ftp_bp.route('/builtin/start', methods=['POST'])
def start_builtin_ftp():
    """启动内置FTP服务器"""
    result = ftp_manager.start()
    return jsonify(result)


@ftp_bp.route('/builtin/stop', methods=['POST'])
def stop_builtin_ftp():
    """停止内置FTP服务器"""
    result = ftp_manager.stop()
    return jsonify(result)


@ftp_bp.route('/builtin/restart', methods=['POST'])
def restart_builtin_ftp():
    """重启内置FTP服务器"""
    result = ftp_manager.restart()
    return jsonify(result)
