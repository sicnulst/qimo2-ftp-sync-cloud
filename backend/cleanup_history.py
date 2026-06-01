"""清理历史记录 + 重置ID"""
import sqlite3, os

DB = os.path.join(os.path.dirname(__file__), 'data', 'sync.db')
conn = sqlite3.connect(DB)
c = conn.cursor()

# 清除所有旧历史记录
c.execute('DELETE FROM sync_history')
print('清除历史记录')

# 清除所有快照
c.execute('DELETE FROM sync_snapshots')
print('清除快照')

# 重置自增ID
for table in ['sync_history', 'sync_tasks', 'ftp_servers', 'users']:
    c.execute(f'DELETE FROM sqlite_sequence WHERE name="{table}"')
print('重置自增ID')

conn.commit()
conn.close()
print('清理完成')
