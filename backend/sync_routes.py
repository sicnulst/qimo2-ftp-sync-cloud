"""
同步任务管理API
"""
import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import get_db
from watcher import file_watcher
from scheduler import scan_scheduler
from sync_engine import sync_engine, SyncTaskFactory
from path_utils import normalize_path
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
from ftplib import FTP

sync_bp = Blueprint('sync', __name__)


def get_local_folder_size(path):
    """计算本地文件夹大小"""
    total_size = 0
    if not os.path.exists(path):
        return 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total_size += os.path.getsize(fp)
            except:
                pass
    return total_size


def get_remote_folder_size(ftp_config, remote_path):
    """计算远程文件夹大小（快速模式，只统计根目录不递归，超时3秒）"""
    total_size = 0
    try:
        ftp = FTP()
        ftp.connect(ftp_config['host'], ftp_config['port'], timeout=3)
        if ftp_config.get('username'):
            ftp.login(ftp_config['username'], ftp_config.get('password', ''))
        else:
            ftp.login()
        ftp.set_pasv(True)
        
        # 切换到远程路径
        try:
            ftp.cwd(remote_path)
        except:
            pass
        
        def calculate_size(line):
            nonlocal total_size
            parts = line.split(None, 8)
            if len(parts) >= 9 and not parts[0].startswith('d'):
                try:
                    total_size += int(parts[4])
                except:
                    pass
        
        ftp.retrlines('LIST', calculate_size)
        ftp.quit()
    except:
        pass
    return total_size


def format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {units[i]}"


@sync_bp.route('/tasks', methods=['GET'])
@jwt_required()
def list_tasks():
    """获取同步任务列表（含状态信息）"""
    user_id = get_jwt_identity()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT st.*, fs.name as server_name, fs.host, fs.port, fs.username, fs.password
        FROM sync_tasks st
        JOIN ftp_servers fs ON st.ftp_server_id = fs.id
        WHERE st.user_id = ?
    ''', (user_id,))
    tasks = []
    for row in cursor.fetchall():
        task = dict(row)
        # 自动转换路径（兼容已有Windows路径记录）
        task['local_path'] = normalize_path(task['local_path'])
        
        # 计算本地文件夹大小
        local_size = get_local_folder_size(task['local_path'])
        task['local_size'] = local_size
        task['local_size_formatted'] = format_size(local_size)
        
        # 计算服务器文件夹大小
        ftp_config = {
            'host': task['host'],
            'port': task['port'],
            'username': task['username'],
            'password': task['password']
        }
        remote_size = get_remote_folder_size(ftp_config, task.get('remote_path', '/'))
        task['remote_size'] = remote_size
        task['remote_size_formatted'] = format_size(remote_size)
        
        # 同步状态
        task['sync_status'] = get_sync_status(task)
        
        # 是否正在监控
        task['is_watching'] = task['id'] in file_watcher.observers
        
        tasks.append(task)
    
    conn.close()
    return jsonify({'tasks': tasks})


def get_sync_status(task):
    """获取同步状态"""
    if not task['is_active']:
        return 'stopped'
    if task['is_syncing']:
        return 'syncing'
    if task['last_sync_time']:
        return 'synced'
    return 'pending'


@sync_bp.route('/tasks', methods=['POST'])
@jwt_required()
def create_task():
    """创建同步任务"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    ftp_server_id = data.get('ftp_server_id')
    local_path = normalize_path(data.get('local_path', '').strip())
    sync_strategy = data.get('sync_strategy', 'newest')
    force_direction = data.get('force_direction', 'none')
    scan_interval = data.get('scan_interval', 60)
    auto_sync = data.get('auto_sync', True)
    delete_sync = data.get('delete_sync', False)
    
    # 自动从 sync_strategy 映射 force_direction
    if sync_strategy == 'force_local':
        force_direction = 'local'
    elif sync_strategy == 'force_remote':
        force_direction = 'remote'
    
    if not ftp_server_id or not local_path:
        return jsonify({'error': 'FTP服务器和本地路径不能为空'}), 400
    
    # 自动获取FTP服务器的隔离路径作为remote_path
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, remote_path FROM ftp_servers WHERE id = ? AND user_id = ?', (ftp_server_id, user_id))
    server = cursor.fetchone()
    if not server:
        conn.close()
        return jsonify({'error': 'FTP服务器不存在'}), 404
    remote_path = server['remote_path']  # 使用服务器的隔离路径，不接受用户输入
    
    # WSL下Windows挂载路径inotify不可靠，自动缩短扫描间隔
    from path_utils import get_is_wsl
    if get_is_wsl() and local_path.startswith('/mnt/'):
        if scan_interval > 15:
            scan_interval = 10
    
    # 创建本地目录
    os.makedirs(local_path, exist_ok=True)
    
    # 创建任务
    cursor.execute('''
        INSERT INTO sync_tasks (user_id, ftp_server_id, local_path, remote_path, sync_strategy, force_direction, delete_sync, scan_interval)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, ftp_server_id, local_path, remote_path, sync_strategy, force_direction, 1 if delete_sync else 0, scan_interval))
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    
    # 自动启动监控和定时扫描
    if auto_sync:
        file_watcher.start_watching(task_id, local_path)
        scan_scheduler.add_job(task_id, scan_interval)
    
    return jsonify({
        'message': '任务创建成功',
        'task': {
            'id': task_id,
            'local_path': local_path,
            'remote_path': remote_path,
            'sync_strategy': sync_strategy
        }
    }), 201


@sync_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    """删除同步任务"""
    user_id = get_jwt_identity()
    
    # 停止监控和定时任务
    file_watcher.stop_watching(task_id)
    scan_scheduler.remove_job(task_id)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sync_tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    if affected == 0:
        return jsonify({'error': '任务不存在'}), 404
    
    return jsonify({'message': '任务删除成功'})


@sync_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    """更新同步任务配置"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sync_tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
    task = cursor.fetchone()
    if not task:
        conn.close()
        return jsonify({'error': '任务不存在'}), 404
    
    # 可更新的字段
    sync_strategy = data.get('sync_strategy', task['sync_strategy'])
    scan_interval = data.get('scan_interval', task['scan_interval'])
    delete_sync = data.get('delete_sync', bool(task['delete_sync']))
    
    # 自动映射 force_direction
    force_direction = task['force_direction']
    if sync_strategy == 'force_local':
        force_direction = 'local'
    elif sync_strategy == 'force_remote':
        force_direction = 'remote'
    elif sync_strategy in ('newest', 'size'):
        force_direction = 'none'
    
    cursor.execute('''
        UPDATE sync_tasks SET sync_strategy = ?, force_direction = ?, scan_interval = ?, delete_sync = ?
        WHERE id = ?
    ''', (sync_strategy, force_direction, scan_interval, 1 if delete_sync else 0, task_id))
    conn.commit()
    conn.close()
    
    # 如果任务正在运行，更新调度器间隔
    from scheduler import scan_scheduler
    if task_id in scan_scheduler.jobs:
        scan_scheduler.remove_job(task_id)
        scan_scheduler.add_job(task_id, scan_interval)
    
    return jsonify({'message': '任务更新成功'})


@sync_bp.route('/tasks/<int:task_id>/start', methods=['POST'])
@jwt_required()
def start_task(task_id):
    """启动任务监控"""
    user_id = get_jwt_identity()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sync_tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
    task = cursor.fetchone()
    conn.close()
    
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    
    local_path = normalize_path(task['local_path'])
    file_watcher.start_watching(task_id, local_path)
    scan_scheduler.add_job(task_id, task['scan_interval'])
    
    # 更新状态
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE sync_tasks SET is_active = 1 WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': '任务已启动'})


@sync_bp.route('/tasks/<int:task_id>/stop', methods=['POST'])
@jwt_required()
def stop_task(task_id):
    """停止任务监控"""
    user_id = get_jwt_identity()
    
    file_watcher.stop_watching(task_id)
    scan_scheduler.remove_job(task_id)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE sync_tasks SET is_active = 0 WHERE id = ? AND user_id = ?', (task_id, user_id))
    conn.commit()
    conn.close()
    
    return jsonify({'message': '任务已停止'})


@sync_bp.route('/tasks/<int:task_id>/pause', methods=['POST'])
@jwt_required()
def pause_task(task_id):
    """暂停任务（保留配置但停止同步）"""
    user_id = get_jwt_identity()
    
    file_watcher.stop_watching(task_id)
    scan_scheduler.remove_job(task_id)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE sync_tasks SET is_active = 0, is_syncing = 0 WHERE id = ? AND user_id = ?', (task_id, user_id))
    conn.commit()
    conn.close()
    
    return jsonify({'message': '任务已暂停'})


@sync_bp.route('/tasks/<int:task_id>/sync', methods=['POST'])
@jwt_required()
def manual_sync(task_id):
    """手动触发同步"""
    user_id = get_jwt_identity()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT st.*, fs.host, fs.port, fs.username, fs.password
        FROM sync_tasks st
        JOIN ftp_servers fs ON st.ftp_server_id = fs.id
        WHERE st.id = ? AND st.user_id = ?
    ''', (task_id, user_id))
    task_row = cursor.fetchone()
    
    if not task_row:
        conn.close()
        return jsonify({'error': '任务不存在'}), 404
    
    # 标记为同步中
    cursor.execute('UPDATE sync_tasks SET is_syncing = 1 WHERE id = ?', (task_id,))
    conn.commit()
    
    task_config = dict(task_row)
    task_config['local_path'] = normalize_path(task_config['local_path'])
    task_config['delete_sync'] = bool(task_config.get('delete_sync', 0))  # 新增：删除同步
    
    # 获取忽略规则
    cursor.execute('SELECT pattern FROM ignore_rules WHERE sync_task_id = ?', (task_id,))
    task_config['ignore_rules'] = [{'pattern': row['pattern']} for row in cursor.fetchall()]
    
    task_config['ftp_config'] = {
        'host': task_config['host'],
        'port': task_config['port'],
        'username': task_config['username'],
        'password': task_config['password']
    }
    
    conn.close()
    
    # 执行同步
    task = SyncTaskFactory.create_task(task_config)
    results = sync_engine.sync(task)
    
    # 保存历史并更新状态
    conn = get_db()
    cursor = conn.cursor()
    for result in results:
        if result.get('file'):
            # 清理路径：去掉内部 user_*/ 前缀
            clean_path = result['file']
            if clean_path.startswith('user_'):
                parts = clean_path.split('/', 2)
                if len(parts) >= 3:
                    clean_path = parts[2]
            
            cursor.execute('''
                INSERT INTO sync_history (sync_task_id, file_name, file_path, direction, action, status, error_message, sync_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_id,
                os.path.basename(clean_path),
                clean_path,
                result.get('direction', 'unknown'),
                result.get('action', 'unknown'),
                result.get('status', 'unknown'),
                result.get('error'),
                datetime.now(CST).isoformat()
            ))
    # 同步完成后，清除 is_syncing 标志
    cursor.execute('UPDATE sync_tasks SET last_sync_time = ?, is_syncing = 0 WHERE id = ?', (datetime.now(CST).isoformat(), task_id))
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': '同步完成',
        'results': results,
        'synced_count': len([r for r in results if r.get('status') == 'success']),
        'error_count': len([r for r in results if r.get('status') == 'error'])
    })


@sync_bp.route('/tasks/<int:task_id>/ignore', methods=['GET'])
@jwt_required()
def get_ignore_rules(task_id):
    """获取忽略规则"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ignore_rules WHERE sync_task_id = ?', (task_id,))
    rules = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'rules': rules})


@sync_bp.route('/tasks/<int:task_id>/ignore', methods=['POST'])
@jwt_required()
def add_ignore_rule(task_id):
    """添加忽略规则"""
    data = request.get_json()
    pattern = data.get('pattern', '').strip()
    
    if not pattern:
        return jsonify({'error': '规则不能为空'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO ignore_rules (sync_task_id, pattern) VALUES (?, ?)', (task_id, pattern))
    conn.commit()
    rule_id = cursor.lastrowid
    conn.close()
    
    return jsonify({
        'message': '规则添加成功',
        'rule': {'id': rule_id, 'pattern': pattern}
    }), 201


@sync_bp.route('/tasks/<int:task_id>/ignore/<int:rule_id>', methods=['DELETE'])
@jwt_required()
def delete_ignore_rule(task_id, rule_id):
    """删除忽略规则"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM ignore_rules WHERE id = ? AND sync_task_id = ?', (rule_id, task_id))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    if affected == 0:
        return jsonify({'error': '规则不存在'}), 404
    
    return jsonify({'message': '规则删除成功'})


@sync_bp.route('/watcher/status', methods=['GET'])
def watcher_status():
    """获取监控器状态"""
    return jsonify(file_watcher.get_status())


@sync_bp.route('/scheduler/status', methods=['GET'])
def scheduler_status():
    """获取调度器状态"""
    return jsonify(scan_scheduler.get_status())
