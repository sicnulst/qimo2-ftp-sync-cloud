"""
同步历史记录API
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import get_db

history_bp = Blueprint('history', __name__)


@history_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    """获取同步统计"""
    user_id = get_jwt_identity()
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 总同步次数
    cursor.execute('''
        SELECT COUNT(*) as total 
        FROM sync_history sh
        JOIN sync_tasks st ON sh.sync_task_id = st.id
        WHERE st.user_id = ?
    ''', (user_id,))
    total = cursor.fetchone()['total']
    
    # 成功次数
    cursor.execute('''
        SELECT COUNT(*) as success 
        FROM sync_history sh
        JOIN sync_tasks st ON sh.sync_task_id = st.id
        WHERE st.user_id = ? AND sh.status = 'success'
    ''', (user_id,))
    success = cursor.fetchone()['success']
    
    # 按方向统计
    cursor.execute('''
        SELECT sh.direction, COUNT(*) as count 
        FROM sync_history sh
        JOIN sync_tasks st ON sh.sync_task_id = st.id
        WHERE st.user_id = ?
        GROUP BY sh.direction
    ''', (user_id,))
    by_direction = {row['direction']: row['count'] for row in cursor.fetchall()}
    
    # 按操作统计
    cursor.execute('''
        SELECT sh.action, COUNT(*) as count 
        FROM sync_history sh
        JOIN sync_tasks st ON sh.sync_task_id = st.id
        WHERE st.user_id = ?
        GROUP BY sh.action
    ''', (user_id,))
    by_action = {row['action']: row['count'] for row in cursor.fetchall()}
    
    conn.close()
    
    return jsonify({
        'total': total,
        'success': success,
        'failed': total - success,
        'by_direction': by_direction,
        'by_action': by_action
    })


@history_bp.route('/all', methods=['GET'])
@jwt_required()
def get_all_history():
    """获取所有同步历史"""
    user_id = get_jwt_identity()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 获取总数
    cursor.execute('''
        SELECT COUNT(*) as total 
        FROM sync_history sh
        JOIN sync_tasks st ON sh.sync_task_id = st.id
        WHERE st.user_id = ?
    ''', (user_id,))
    total = cursor.fetchone()['total']
    
    # 获取分页数据
    offset = (page - 1) * per_page
    cursor.execute('''
        SELECT sh.*, st.local_path 
        FROM sync_history sh
        JOIN sync_tasks st ON sh.sync_task_id = st.id
        WHERE st.user_id = ?
        ORDER BY sh.sync_time DESC 
        LIMIT ? OFFSET ?
    ''', (user_id, per_page, offset))
    
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({
        'history': history,
        'total': total,
        'page': page,
        'per_page': per_page
    })


@history_bp.route('/<int:task_id>', methods=['GET'])
@jwt_required()
def get_history(task_id):
    """获取同步历史"""
    user_id = get_jwt_identity()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 验证任务属于当前用户
    cursor.execute('SELECT id FROM sync_tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': '任务不存在'}), 404
    
    # 获取总数
    cursor.execute('SELECT COUNT(*) as total FROM sync_history WHERE sync_task_id = ?', (task_id,))
    total = cursor.fetchone()['total']
    
    # 获取分页数据
    offset = (page - 1) * per_page
    cursor.execute('''
        SELECT * FROM sync_history 
        WHERE sync_task_id = ? 
        ORDER BY sync_time DESC 
        LIMIT ? OFFSET ?
    ''', (task_id, per_page, offset))
    
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({
        'history': history,
        'total': total,
        'page': page,
        'per_page': per_page
    })
