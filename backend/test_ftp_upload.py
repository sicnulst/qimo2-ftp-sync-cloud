"""
FTP连接测试脚本
在Windows PowerShell中运行：python test_ftp_upload.py
"""
from ftplib import FTP, all_errors
import os
import sys

# 创建测试文件
test_file = r'C:\temp\test_ftp.txt'
os.makedirs(r'C:\temp', exist_ok=True)
with open(test_file, 'w') as f:
    f.write('This is a test file for FTP upload')

print("=" * 50)
print("FTP连接测试")
print("=" * 50)

# 测试1: 被动模式
print("\n[测试1] 被动模式上传...")
try:
    ftp = FTP()
    ftp.connect('127.0.0.1', 2121, timeout=30)
    print(f"  连接成功: {ftp.getwelcome()}")
    
    ftp.login('admin', 'admin123')
    print("  登录成功")
    
    ftp.set_pasv(True)
    print("  被动模式已设置")
    
    with open(test_file, 'rb') as f:
        ftp.storbinary('STOR /test.txt', f)
    print("  ✓ 上传成功!")
    ftp.quit()
except all_errors as e:
    print(f"  ✗ 失败: {e}")
    
    # 测试2: 主动模式
    print("\n[测试2] 主动模式上传...")
    try:
        ftp = FTP()
        ftp.connect('127.0.0.1', 2121, timeout=30)
        ftp.login('admin', 'admin123')
        ftp.set_pasv(False)
        print("  主动模式已设置")
        
        with open(test_file, 'rb') as f:
            ftp.storbinary('STOR /test.txt', f)
        print("  ✓ 主动模式上传成功!")
        ftp.quit()
    except all_errors as e2:
        print(f"  ✗ 主动模式也失败: {e2}")
        
        # 测试3: 详细错误
        print("\n[测试3] 详细诊断...")
        try:
            ftp = FTP()
            ftp.connect('127.0.0.1', 2121, timeout=30)
            ftp.login('admin', 'admin123')
            
            # 测试目录操作
            print("  测试 LIST...")
            files = []
            ftp.retrlines('LIST', files.append)
            print(f"  LIST 成功，文件数: {len(files)}")
            
            # 测试 STOR
            print("  测试 STOR...")
            ftp.set_pasv(False)
            with open(test_file, 'rb') as f:
                ftp.storbinary('STOR /test.txt', f)
            print("  STOR 成功!")
            ftp.quit()
        except Exception as e3:
            print(f"  详细错误: {type(e3).__name__}: {e3}")

print("\n" + "=" * 50)
print("测试完成")
print("=" * 50)

input("\n按Enter键退出...")
