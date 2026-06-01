# -*- coding: utf-8 -*-
from ftplib import FTP
import os

print("FTP上传测试")
print("=" * 40)

# 创建测试文件
test_file = r'C:\temp\test_ftp.txt'
os.makedirs(r'C:\temp', exist_ok=True)
with open(test_file, 'w') as f:
    f.write('test content for FTP upload')

# 测试主动模式
print("\n[1] 主动模式测试...")
try:
    ftp = FTP()
    ftp.connect('127.0.0.1', 2121, timeout=30)
    ftp.login('admin', 'admin123')
    ftp.set_pasv(False)  # 主动模式
    print("  connect ok: " + ftp.getwelcome())
    
    with open(test_file, 'rb') as f:
        ftp.storbinary('STOR /test.txt', f)
    print("  upload ok!")
    ftp.quit()
except Exception as e:
    print("  fail: " + str(e))

# 测试被动模式
print("\n[2] passive mode test...")
try:
    ftp = FTP()
    ftp.connect('127.0.0.1', 2121, timeout=30)
    ftp.login('admin', 'admin123')
    ftp.set_pasv(True)  # 被动模式
    print("  connect ok: " + ftp.getwelcome())
    
    with open(test_file, 'rb') as f:
        ftp.storbinary('STOR /test2.txt', f)
    print("  upload ok!")
    ftp.quit()
except Exception as e:
    print("  fail: " + str(e))

print("\n" + "=" * 40)
print("test done")
