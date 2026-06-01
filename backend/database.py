"""
数据库初始化模块
使用SQLite存储用户、FTP配置、同步任务、同步历史
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'sync.db')


def get_db():
    """获取数据库连接（单例模式）"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表结构"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # FTP服务器配置表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ftp_servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            host TEXT NOT NULL,
            port INTEGER DEFAULT 21,
            username TEXT,
            password TEXT,
            remote_path TEXT DEFAULT '/',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # 同步任务表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ftp_server_id INTEGER NOT NULL,
            local_path TEXT NOT NULL,
            remote_path TEXT DEFAULT '/',
            sync_strategy TEXT DEFAULT 'newest',
            force_direction TEXT DEFAULT 'none',
            delete_sync INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            is_syncing INTEGER DEFAULT 0,
            last_sync_time TIMESTAMP,
            scan_interval INTEGER DEFAULT 60,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (ftp_server_id) REFERENCES ftp_servers(id)
        )
    ''')
    
    # 忽略列表表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ignore_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_task_id INTEGER NOT NULL,
            pattern TEXT NOT NULL,
            rule_type TEXT DEFAULT 'glob',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sync_task_id) REFERENCES sync_tasks(id) ON DELETE CASCADE
        )
    ''')
    
    # 同步历史表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_task_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            direction TEXT NOT NULL,
            action TEXT NOT NULL,
            file_size INTEGER,
            sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'success',
            error_message TEXT,
            FOREIGN KEY (sync_task_id) REFERENCES sync_tasks(id)
        )
    ''')

    # 同步快照表（记录上次同步状态，防止死循环）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_task_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            local_size INTEGER,
            local_mtime REAL,
            remote_size INTEGER,
            last_sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(sync_task_id, file_path),
            FOREIGN KEY (sync_task_id) REFERENCES sync_tasks(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()
    print("数据库初始化完成")


if __name__ == '__main__':
    init_db()
