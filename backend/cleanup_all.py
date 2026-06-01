"""清理所有脏数据：FTP存储 + 本地同步文件夹 + 数据库"""
import sqlite3, os, shutil

BASE = os.path.dirname(__file__)
DB = os.path.join(BASE, 'data', 'sync.db')

# 1. 清理FTP存储中的嵌套脏数据
ftp_root = os.path.join(BASE, 'ftp_storage')
for user_dir in os.listdir(ftp_root):
    user_path = os.path.join(ftp_root, user_dir)
    if not os.path.isdir(user_path):
        continue
    for server_dir in os.listdir(user_path):
        server_path = os.path.join(user_path, server_dir)
        if not os.path.isdir(server_path):
            continue
        # 删除嵌套的 user_* 目录（旧bug产生的脏数据）
        for item in os.listdir(server_path):
            item_path = os.path.join(server_path, item)
            if item.startswith('user_') and os.path.isdir(item_path):
                shutil.rmtree(item_path)
                print(f'删除脏目录: {server_path}/{item}')
        # 删除测试遗留文件
        for f in ['delete_test.txt', 'delete_test2.txt', 'brand_new_file.txt', 'new_file_test.txt', 'history_test.txt']:
            fp = os.path.join(server_path, f)
            if os.path.exists(fp):
                os.remove(fp)
                print(f'删除测试文件: {server_path}/{f}')

# 2. 清理本地同步文件夹中的测试文件
local_base = '/mnt/c/Users/20231/Desktop/人机交互'
for folder in ['yun1', 'yun2', 'yun3', 'yunpan4']:
    folder_path = os.path.join(local_base, folder)
    if not os.path.exists(folder_path):
        continue
    for f in ['delete_test.txt', 'delete_test2.txt', 'brand_new_file.txt', 'new_file_test.txt', 'history_test.txt']:
        fp = os.path.join(folder_path, f)
        if os.path.exists(fp):
            os.remove(fp)
            print(f'删除本地测试文件: {fp}')
    # 删除嵌套的 user_* 目录
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if item.startswith('user_') and os.path.isdir(item_path):
            shutil.rmtree(item_path)
            print(f'删除本地脏目录: {item_path}')

# 3. 清理数据库
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute('DELETE FROM sync_history')
c.execute('DELETE FROM sync_snapshots')
for t in ['sync_history', 'sync_snapshots']:
    c.execute(f'DELETE FROM sqlite_sequence WHERE name="{t}"')
conn.commit()
conn.close()
print('数据库历史+快照已清理')

print('全部清理完成')
