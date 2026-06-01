"""
用户认证模块
JWT认证 + 密码哈希
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    if len(username) < 3 or len(password) < 6:
        return jsonify({'error': '用户名至少3位，密码至少6位'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 检查用户名是否已存在
    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': '用户名已存在'}), 409
    
    # 创建用户
    password_hash = generate_password_hash(password)
    cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                   (username, password_hash))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    
    # 生成JWT
    access_token = create_access_token(identity=str(user_id))
    
    return jsonify({
        'message': '注册成功',
        'user': {'id': user_id, 'username': username},
        'access_token': access_token
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, password_hash FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': '用户名或密码错误'}), 401
    
    access_token = create_access_token(identity=str(user['id']))
    
    return jsonify({
        'message': '登录成功',
        'user': {'id': user['id'], 'username': user['username']},
        'access_token': access_token
    })


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    """获取用户信息"""
    user_id = get_jwt_identity()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, created_at FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    
    return jsonify({
        'id': user['id'],
        'username': user['username'],
        'created_at': user['created_at']
    })
