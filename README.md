# FTP私有同步云盘系统

基于Flask + watchdog + pyftpdlib的文件自动同步解决方案

## 功能特性

### 核心功能
- **用户认证登录**：JWT认证，支持注册/登录
- **多FTP服务器管理**：支持添加多个FTP服务器，测试连接，浏览远程文件
- **同步任务管理**：创建/启动/停止/删除同步任务
- **自动文件同步**：watchdog监控本地文件变化，自动同步到FTP服务器
- **定时扫描**：APScheduler定时扫描，发现变更自动同步
- **忽略列表**：支持glob模式匹配，忽略不需要同步的文件

### 同步策略
- **最新优先**：以最后修改时间为准，同步最新版本
- **大小优先**：以文件大小为准，大小不同则同步
- **强制本地**：强制以本地文件为准，上传到服务器
- **强制服务器**：强制以服务器文件为准，下载到本地

### 扩展功能
- **WebSocket实时推送**：同步状态实时更新
- **同步历史记录**：完整的同步历史，支持分页查询
- **文件浏览器**：同时浏览本地和服务器文件
- **统计面板**：同步成功率、任务数量等统计

## 技术栈

| 组件 | 技术 |
|------|------|
| 前端框架 | Vue3 + Element Plus + Vite |
| 后端框架 | Flask + Flask-SocketIO |
| FTP服务器 | pyftpdlib (miniFTP) |
| 文件监控 | watchdog |
| 定时任务 | APScheduler |
| 数据库 | SQLite |
| 认证方式 | JWT |

## 快速开始

### 1. 启动后端
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### 2. 启动前端
```bash
cd frontend
npm install
npm run dev
```

### 3. 访问
打开浏览器访问 http://localhost:3000
