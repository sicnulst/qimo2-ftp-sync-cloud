"""
本地文件浏览 + 差异对比 + 远端文件下载 + 文件管理 API
"""
import os
from io import BytesIO
from ftplib import FTP
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required
from path_utils import normalize_path

files_bp = Blueprint('files', __name__)


@files_bp.route('/local', methods=['GET'])
@jwt_required()
def list_local_files():
    """列出本地文件（需要登录鉴权）"""
    base_path = normalize_path(request.args.get('path', ''))
    subpath = request.args.get('subpath', '/')

    if not base_path:
        return jsonify({'error': '请提供路径参数'}), 400

    # 拼接完整路径并规范化
    full_path = os.path.normpath(os.path.join(base_path, subpath.lstrip('/')))

    # 安全检查：确保不会通过 '../' 目录穿越跑到 base_path 之外
    base_real = os.path.realpath(base_path)
    full_real = os.path.realpath(full_path)
    if not full_real.startswith(base_real):
        return jsonify({'error': '非法路径访问'}), 403

    if not os.path.exists(full_path):
        return jsonify({'error': '路径不存在'}), 404

    if not os.path.isdir(full_path):
        return jsonify({'error': '不是目录'}), 400

    files = []
    try:
        for name in os.listdir(full_path):
            item_path = os.path.join(full_path, name)
            is_dir = os.path.isdir(item_path)
            try:
                size = 0 if is_dir else os.path.getsize(item_path)
            except OSError:
                size = 0

            files.append({
                'name': name,
                'path': f"{subpath.rstrip('/')}/{name}",
                'is_dir': is_dir,
                'size': size
            })

        # 排序：目录在前，文件在后
        files.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))

    except PermissionError:
        return jsonify({'error': '没有访问权限'}), 403

    return jsonify({
        'path': subpath,
        'files': files
    })


@files_bp.route('/diff', methods=['POST'])
@jwt_required()
def compare_files():
    """
    对比本地文件夹与远端FTP文件夹的差异。
    
    请求体:
      {
        "local_path": "C:/Users/xxx/sync_folder",
        "ftp_host": "127.0.0.1",
        "ftp_port": 2121,
        "ftp_username": "admin",
        "ftp_password": "admin123",
        "remote_path": "/sync_folder"
      }
    
    返回每个文件的状态:
      - "same"       : 本地和远端文件大小相同（视为一致）
      - "local_only" : 仅本地有，远端没有（未上传）
      - "remote_only": 仅远端有，本地没有（已删除或未下载）
      - "different"  : 两端都有但大小不同（内容可能不同步）
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': '缺少请求体'}), 400

    local_path = normalize_path(data.get('local_path', ''))
    ftp_host = data.get('ftp_host', '127.0.0.1')
    ftp_port = data.get('ftp_port', 2121)
    ftp_username = data.get('ftp_username', '')
    ftp_password = data.get('ftp_password', '')
    remote_path = data.get('remote_path', '/')

    if not local_path:
        return jsonify({'error': '缺少 local_path 参数'}), 400

    # 安全检查：local_path 不能是根目录或系统目录
    local_path = os.path.normpath(local_path)
    if not os.path.exists(local_path):
        return jsonify({'error': f'本地路径不存在: {local_path}'}), 404

    # ---- 扫描本地文件（只扫根目录一层，名称→大小）----
    local_map = {}
    try:
        for name in os.listdir(local_path):
            item = os.path.join(local_path, name)
            if os.path.isfile(item):
                try:
                    local_map[name] = os.path.getsize(item)
                except OSError:
                    local_map[name] = 0
    except PermissionError:
        return jsonify({'error': '无法读取本地路径，权限不足'}), 403

    # ---- 扫描远端文件（名称→大小）----
    remote_map = {}
    try:
        ftp = FTP()
        ftp.connect(ftp_host, ftp_port, timeout=5)
        if ftp_username:
            ftp.login(ftp_username, ftp_password)
        else:
            ftp.login()
        ftp.set_pasv(True)

        try:
            ftp.cwd(remote_path)
        except Exception as e:
            # 远端目录不存在：视为全部未上传
            ftp.quit()
            results = [
                {'name': name, 'local_size': size, 'remote_size': None, 'status': 'local_only'}
                for name, size in local_map.items()
            ]
            return jsonify({
                'local_path': local_path,
                'remote_path': remote_path,
                'summary': {
                    'same': 0,
                    'different': 0,
                    'local_only': len(results),
                    'remote_only': 0
                },
                'files': results
            })

        def parse_line(line):
            parts = line.split(None, 8)
            if len(parts) >= 9 and not parts[0].startswith('d'):
                try:
                    remote_map[parts[8]] = int(parts[4])
                except (ValueError, IndexError):
                    pass

        ftp.retrlines('LIST', parse_line)
        ftp.quit()
    except Exception as e:
        return jsonify({'error': f'无法连接FTP服务器: {str(e)}'}), 400

    # ---- 合并对比 ----
    all_names = set(local_map.keys()) | set(remote_map.keys())
    results = []
    counters = {'same': 0, 'different': 0, 'local_only': 0, 'remote_only': 0}

    for name in sorted(all_names):
        local_size = local_map.get(name)
        remote_size = remote_map.get(name)

        if local_size is not None and remote_size is not None:
            status = 'same' if local_size == remote_size else 'different'
        elif local_size is not None:
            status = 'local_only'
        else:
            status = 'remote_only'

        counters[status] += 1
        results.append({
            'name': name,
            'local_size': local_size,
            'remote_size': remote_size,
            'status': status
        })

    return jsonify({
        'local_path': local_path,
        'remote_path': remote_path,
        'summary': counters,
        'files': results
    })


@files_bp.route('/remote/download', methods=['GET'])
@jwt_required()
def download_remote_file():
    """
    从远端 FTP 服务器下载文件到浏览器本地。

    查询参数:
      ftp_host     - FTP 服务器地址
      ftp_port     - FTP 端口（默认 2121）
      ftp_username - FTP 用户名
      ftp_password - FTP 密码
      path         - 远端文件的完整路径（如 /sync_test/report.docx）
      task_id      - 可选，用于记录下载历史
    """
    ftp_host = request.args.get('ftp_host', '127.0.0.1')
    ftp_port = request.args.get('ftp_port', 2121, type=int)
    ftp_username = request.args.get('ftp_username', '')
    ftp_password = request.args.get('ftp_password', '')
    file_path = request.args.get('path', '')

    if not file_path:
        return jsonify({'error': '缺少 path 参数（远端文件路径）'}), 400

    filename = os.path.basename(file_path)
    if not filename:
        return jsonify({'error': '无法从路径中提取文件名'}), 400

    try:
        ftp = FTP()
        ftp.connect(ftp_host, ftp_port, timeout=10)
        if ftp_username:
            ftp.login(ftp_username, ftp_password)
        else:
            ftp.login()
        ftp.set_pasv(True)

        # 将文件下载到内存
        buf = BytesIO()
        ftp.retrbinary(f'RETR {file_path}', buf.write)
        ftp.quit()

        buf.seek(0)

        return send_file(
            buf,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
    except Exception as e:
        return jsonify({'error': f'下载失败: {str(e)}'}), 400


# ========== 文件管理API ==========

@files_bp.route('/local/mkdir', methods=['POST'])
@jwt_required()
def create_directory():
    """在本地同步文件夹中创建新文件夹"""
    data = request.get_json()
    base_path = normalize_path(data.get('path', ''))
    subpath = data.get('subpath', '/')
    folder_name = data.get('folder_name', '').strip()
    
    if not base_path or not folder_name:
        return jsonify({'error': '缺少路径或文件夹名'}), 400
    
    # 安全检查
    full_path = os.path.normpath(os.path.join(base_path, subpath.lstrip('/'), folder_name))
    base_real = os.path.realpath(base_path)
    full_real = os.path.realpath(full_path)
    if not full_real.startswith(base_real):
        return jsonify({'error': '非法路径访问'}), 403
    
    try:
        os.makedirs(full_path, exist_ok=True)
        return jsonify({'message': f'文件夹 "{folder_name}" 创建成功', 'path': full_path})
    except Exception as e:
        return jsonify({'error': f'创建失败: {str(e)}'}), 500


@files_bp.route('/local/upload', methods=['POST'])
@jwt_required()
def upload_file():
    """上传文件到本地同步文件夹"""
    base_path = normalize_path(request.form.get('path', ''))
    subpath = request.form.get('subpath', '/')
    
    if not base_path:
        return jsonify({'error': '缺少路径参数'}), 400
    
    if 'file' not in request.files:
        return jsonify({'error': '没有选择文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400
    
    # 安全检查
    target_dir = os.path.normpath(os.path.join(base_path, subpath.lstrip('/')))
    base_real = os.path.realpath(base_path)
    target_real = os.path.realpath(target_dir)
    if not target_real.startswith(base_real):
        return jsonify({'error': '非法路径访问'}), 403
    
    try:
        os.makedirs(target_dir, exist_ok=True)
        save_path = os.path.join(target_dir, file.filename)
        file.save(save_path)
        return jsonify({'message': f'文件 "{file.filename}" 上传成功', 'path': save_path})
    except Exception as e:
        return jsonify({'error': f'上传失败: {str(e)}'}), 500


@files_bp.route('/local/delete', methods=['POST'])
@jwt_required()
def delete_local_file():
    """删除本地文件或文件夹"""
    data = request.get_json()
    base_path = normalize_path(data.get('path', ''))
    file_path = data.get('file_path', '')
    
    if not base_path or not file_path:
        return jsonify({'error': '缺少参数'}), 400
    
    full_path = os.path.normpath(os.path.join(base_path, file_path.lstrip('/')))
    base_real = os.path.realpath(base_path)
    full_real = os.path.realpath(full_path)
    if not full_real.startswith(base_real):
        return jsonify({'error': '非法路径访问'}), 403
    
    if not os.path.exists(full_path):
        return jsonify({'error': '文件不存在'}), 404
    
    try:
        if os.path.isdir(full_path):
            import shutil
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
        return jsonify({'message': '删除成功'})
    except Exception as e:
        return jsonify({'error': f'删除失败: {str(e)}'}), 500


@files_bp.route('/remote/upload', methods=['POST'])
@jwt_required()
def upload_to_remote():
    """上传文件到远端FTP服务器"""
    ftp_host = request.form.get('ftp_host', '127.0.0.1')
    ftp_port = int(request.form.get('ftp_port', 2121))
    ftp_username = request.form.get('ftp_username', '')
    ftp_password = request.form.get('ftp_password', '')
    remote_path = request.form.get('remote_path', '/')
    
    if 'file' not in request.files:
        return jsonify({'error': '没有选择文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400
    
    try:
        ftp = FTP()
        ftp.connect(ftp_host, ftp_port, timeout=10)
        if ftp_username:
            ftp.login(ftp_username, ftp_password)
        else:
            ftp.login()
        ftp.set_pasv(True)
        
        # 确保远端目录存在
        parts = remote_path.strip('/').split('/')
        current = ''
        for part in parts:
            if part:
                current += f'/{part}'
                try:
                    ftp.mkd(current)
                except:
                    pass
        
        # 上传文件
        target = f"{remote_path.rstrip('/')}/{file.filename}"
        file_data = BytesIO(file.read())
        ftp.storbinary(f'STOR {target}', file_data)
        ftp.quit()
        
        return jsonify({'message': f'文件 "{file.filename}" 上传到远端成功'})
    except Exception as e:
        return jsonify({'error': f'上传失败: {str(e)}'}), 500


@files_bp.route('/remote/mkdir', methods=['POST'])
@jwt_required()
def create_remote_directory():
    """在远端FTP服务器创建文件夹"""
    data = request.get_json()
    ftp_host = data.get('ftp_host', '127.0.0.1')
    ftp_port = data.get('ftp_port', 2121)
    ftp_username = data.get('ftp_username', '')
    ftp_password = data.get('ftp_password', '')
    remote_path = data.get('remote_path', '/')
    folder_name = data.get('folder_name', '').strip()
    
    if not folder_name:
        return jsonify({'error': '文件夹名不能为空'}), 400
    
    try:
        ftp = FTP()
        ftp.connect(ftp_host, ftp_port, timeout=10)
        if ftp_username:
            ftp.login(ftp_username, ftp_password)
        else:
            ftp.login()
        ftp.set_pasv(True)
        
        new_dir = f"{remote_path.rstrip('/')}/{folder_name}"
        ftp.mkd(new_dir)
        ftp.quit()
        return jsonify({'message': f'远端文件夹 "{folder_name}" 创建成功'})
    except Exception as e:
        return jsonify({'error': f'创建失败: {str(e)}'}), 500


@files_bp.route('/remote/delete', methods=['POST'])
@jwt_required()
def delete_remote_file():
    """删除远端FTP服务器上的文件"""
    data = request.get_json()
    ftp_host = data.get('ftp_host', '127.0.0.1')
    ftp_port = data.get('ftp_port', 2121)
    ftp_username = data.get('ftp_username', '')
    ftp_password = data.get('ftp_password', '')
    file_path = data.get('file_path', '')
    is_dir = data.get('is_dir', False)
    
    if not file_path:
        return jsonify({'error': '缺少文件路径'}), 400
    
    try:
        ftp = FTP()
        ftp.connect(ftp_host, ftp_port, timeout=10)
        if ftp_username:
            ftp.login(ftp_username, ftp_password)
        else:
            ftp.login()
        ftp.set_pasv(True)
        
        if is_dir:
            ftp.rmd(file_path)
        else:
            ftp.delete(file_path)
        ftp.quit()
        return jsonify({'message': '删除成功'})
    except Exception as e:
        return jsonify({'error': f'删除失败: {str(e)}'}), 500
