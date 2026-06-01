"""重排所有表的ID为连续编号"""
import sqlite3, os

DB = os.path.join(os.path.dirname(__file__), 'data', 'sync.db')
conn = sqlite3.connect(DB)
c = conn.cursor()

# 暂时关闭外键约束
c.execute('PRAGMA foreign_keys = OFF')

# 1. 重排 users 表
c.execute('SELECT id FROM users ORDER BY id')
old_ids = [r[0] for r in c.fetchall()]
id_map = {}
for new_id, old_id in enumerate(old_ids, 1):
    if new_id != old_id:
        id_map[('users', old_id)] = new_id
        c.execute('UPDATE users SET id = ? WHERE id = ?', (new_id, old_id))

# 2. 重排 ftp_servers 表
c.execute('SELECT id FROM ftp_servers ORDER BY id')
old_ids = [r[0] for r in c.fetchall()]
for new_id, old_id in enumerate(old_ids, 1):
    if new_id != old_id:
        id_map[('ftp_servers', old_id)] = new_id
        c.execute('UPDATE ftp_servers SET id = ? WHERE id = ?', (new_id, old_id))

# 3. 更新 ftp_servers 的 user_id 外键
c.execute('SELECT id, user_id FROM ftp_servers')
for row in c.fetchall():
    new_user_id = id_map.get(('users', row[1]))
    if new_user_id:
        c.execute('UPDATE ftp_servers SET user_id = ? WHERE id = ?', (new_user_id, row[0]))

# 4. 重排 sync_tasks 表
c.execute('SELECT id FROM sync_tasks ORDER BY id')
old_ids = [r[0] for r in c.fetchall()]
for new_id, old_id in enumerate(old_ids, 1):
    if new_id != old_id:
        id_map[('sync_tasks', old_id)] = new_id
        c.execute('UPDATE sync_tasks SET id = ? WHERE id = ?', (new_id, old_id))

# 5. 更新 sync_tasks 的外键
c.execute('SELECT id, user_id, ftp_server_id FROM sync_tasks')
for row in c.fetchall():
    new_user_id = id_map.get(('users', row[1]))
    new_server_id = id_map.get(('ftp_servers', row[2]))
    if new_user_id or new_server_id:
        c.execute('UPDATE sync_tasks SET user_id = COALESCE(?, user_id), ftp_server_id = COALESCE(?, ftp_server_id) WHERE id = ?',
                  (new_user_id, new_server_id, row[0]))

# 6. 更新 ignore_rules 的 sync_task_id
c.execute('SELECT id, sync_task_id FROM ignore_rules')
for row in c.fetchall():
    new_task_id = id_map.get(('sync_tasks', row[1]))
    if new_task_id:
        c.execute('UPDATE ignore_rules SET sync_task_id = ? WHERE id = ?', (new_task_id, row[0]))

# 7. 更新 sync_history 的 sync_task_id
c.execute('SELECT id, sync_task_id FROM sync_history')
for row in c.fetchall():
    new_task_id = id_map.get(('sync_tasks', row[1]))
    if new_task_id:
        c.execute('UPDATE sync_history SET sync_task_id = ? WHERE id = ?', (new_task_id, row[0]))

# 8. 更新 sync_snapshots 的 sync_task_id
c.execute('SELECT id, sync_task_id FROM sync_snapshots')
for row in c.fetchall():
    new_task_id = id_map.get(('sync_tasks', row[1]))
    if new_task_id:
        c.execute('UPDATE sync_snapshots SET sync_task_id = ? WHERE id = ?', (new_task_id, row[0]))

# 9. 重置自增序列
for table in ['users', 'ftp_servers', 'sync_tasks', 'ignore_rules', 'sync_history', 'sync_snapshots']:
    c.execute(f'DELETE FROM sqlite_sequence WHERE name="{table}"')
    c.execute(f'SELECT MAX(id) FROM {table}')
    max_id = c.fetchone()[0]
    if max_id:
        c.execute(f"INSERT INTO sqlite_sequence (name, seq) VALUES ('{table}', {max_id})")

conn.commit()

# 验证
print('=== 重排后 ===')
print('Users:')
for r in conn.execute('SELECT id, username FROM users ORDER BY id'):
    print(f'  ID={r[0]} username={r[1]}')
print('FTP Servers:')
for r in conn.execute('SELECT id, user_id, name FROM ftp_servers ORDER BY id'):
    print(f'  ID={r[0]} user={r[1]} name={r[2]}')
print('Sync Tasks:')
for r in conn.execute('SELECT id, user_id, ftp_server_id FROM sync_tasks ORDER BY id'):
    print(f'  ID={r[0]} user={r[1]} server={r[2]}')

conn.close()
print('ID重排完成')
