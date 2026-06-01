"""
Flask后端主应用
提供REST API支持 + 前端静态文件服务
"""
import os
from datetime import timedelta
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# 前端dist目录
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend', 'dist')

# 创建Flask应用（不用static_folder，手动处理所有静态文件）
app = Flask(__name__)
# 固定密钥：避免每次重启导致 JWT token 失效，用户需重新登录
app.config['SECRET_KEY'] = 'ftp-sync-cloud-secret-2024-stable'
app.config['JWT_SECRET_KEY'] = 'ftp-sync-jwt-secret-2024-stable-key'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# 初始化扩展
CORS(app, resources={r"/api/*": {"origins": "*"}})
jwt = JWTManager(app)

# 导入路由
from auth import auth_bp
from ftp_routes import ftp_bp
from sync_routes import sync_bp
from history_routes import history_bp
from files_routes import files_bp

# 注册蓝图
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(ftp_bp, url_prefix='/api/ftp')
app.register_blueprint(sync_bp, url_prefix='/api/sync')
app.register_blueprint(history_bp, url_prefix='/api/history')
app.register_blueprint(files_bp, url_prefix='/api/files')


@app.route('/api/health')
def health_check():
    """健康检查"""
    return jsonify({'status': 'ok', 'message': '服务运行正常'})


# 前端SPA路由：所有非API路径返回index.html
@app.route('/')
@app.route('/<path:path>')
def serve_frontend(path=''):
    if path and os.path.exists(os.path.join(FRONTEND_DIST, path)):
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, 'index.html')


if __name__ == '__main__':
    from database import init_db
    init_db()
    
    # 启动内置FTP服务器
    from ftp_server import ftp_manager
    result = ftp_manager.start(force=True)
    print(f"FTP服务器: {result}")
    
    # 自动恢复已有的活跃同步任务（重启后不丢失）
    from database import get_db
    from watcher import file_watcher
    from scheduler import scan_scheduler
    from path_utils import normalize_path
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, local_path, scan_interval FROM sync_tasks WHERE is_active = 1')
        active_tasks = cursor.fetchall()
        conn.close()
        for task in active_tasks:
            local_path = normalize_path(task['local_path'])
            file_watcher.start_watching(task['id'], local_path)
            scan_scheduler.add_job(task['id'], task['scan_interval'])
            print(f"恢复任务{task['id']}: {local_path} (间隔{task['scan_interval']}s)")
    except Exception as e:
        print(f"恢复任务失败: {e}")
    
    print("启动Flask服务: http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
