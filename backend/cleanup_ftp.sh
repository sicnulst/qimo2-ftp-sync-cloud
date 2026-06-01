#!/bin/bash
# 清理FTP storage测试文件，创建隔离目录
cd "$(dirname "$0")/ftp_storage" || exit 1

# 删除测试遗留文件
rm -f sync_test.txt
rm -f "新建 DOC 文档.doc"
rm -f "新建 DOCX 文档.docx"
rm -rf auto_test

# 创建隔离目录结构
mkdir -p user_1/测试服务器
mkdir -p user_2/云盘1
mkdir -p user_2/yun2

echo "=== FTP Storage 清理后 ==="
find . -maxdepth 3 -type f -o -type d
