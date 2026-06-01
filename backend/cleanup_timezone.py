"""清理历史记录 + 重置ID + 修复时区"""
import sqlite3, os

DB = os.path.join(os.path.dirname(__file__), 'data', 'sync.db')
conn = sqlite3.connect(DB)
c = conn.cursor()

# 清除所有旧历史记录（时区错误的旧数据）
c.execute('DELETE FROM sync_history')
print('清除旧历史记录（时区错误）')

# 清除快照
c.execute('DELETE FROM sync_snapshots')
print('清除快照')

# 重置自增序列
for table in ['sync_history', 'sync_snapshots']:
    c.execute(f'DELETE FROM sqlite_sequence WHERE name="{table}"')

conn.commit()
conn.close()
print('清理完成')
