"""数据库清理脚本：创建新表 + 清理脏数据 + 隔离路径"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'sync.db')
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# 1. 创建 sync_snapshots 表
c.execute('''
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
print('1. sync_snapshots 表已创建')

# 2. 清除死循环历史
c.execute('SELECT COUNT(*) FROM sync_history')
total = c.fetchone()[0]
c.execute('''
    DELETE FROM sync_history WHERE id NOT IN (
        SELECT id FROM sync_history ORDER BY id DESC LIMIT 10
    )
''')
print(f'2. 历史记录: {total} -> 10')

# 3. 更新FTP服务器 remote_path 为隔离路径
c.execute('SELECT id, user_id, name, remote_path FROM ftp_servers')
servers = c.fetchall()
for s in servers:
    if s['remote_path'] == '/':
        safe_name = s['name'].replace(' ', '_').replace('/', '_')
        new_path = f'/user_{s["user_id"]}/{safe_name}'
        c.execute('UPDATE ftp_servers SET remote_path = ? WHERE id = ?', (new_path, s['id']))
        print(f'3. 服务器{s["id"]}({s["name"]}): / -> {new_path}')

# 4. 更新同步任务 remote_path
c.execute('SELECT id, ftp_server_id, remote_path FROM sync_tasks')
tasks = c.fetchall()
for t in tasks:
    c.execute('SELECT remote_path FROM ftp_servers WHERE id = ?', (t['ftp_server_id'],))
    server = c.fetchone()
    if server and t['remote_path'] == '/':
        c.execute('UPDATE sync_tasks SET remote_path = ? WHERE id = ?', (server['remote_path'], t['id']))
        print(f'4. 任务{t["id"]}: / -> {server["remote_path"]}')

# 5. 清除旧快照
c.execute('DELETE FROM sync_snapshots')
print('5. 旧快照已清除')

conn.commit()
conn.close()
print('数据库清理完成')
