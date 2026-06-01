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
| 后端框架 | Flask + Flask-SocketIO |
| FTP服务器 | pyftpdlib (miniFTP) |
| 文件监控 | watchdog |
| 定时任务 | APScheduler |
| 数据库 | SQLite |
| 前端框架 | Vue3 + Element Plus |
| 认证方式 | JWT |

## 设计模式

1. **单例模式**：FTPServerManager、FTPConnectionPool、FileWatcher、ScanScheduler
2. **观察者模式**：watchdog文件系统事件监控
3. **策略模式**：4种同步策略（NewestStrategy、SizeStrategy、ForceLocalStrategy、ForceRemoteStrategy）
4. **工厂模式**：SyncTaskFactory创建同步任务

## 快速开始

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动后端服务

```bash
cd backend
python app.py
```

后端服务将启动在 http://127.0.0.1:5000
内置FTP服务器将启动在 127.0.0.1:2121

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

### 4. 启动前端服务

```bash
cd frontend
npm run dev
```

前端服务将启动在 http://localhost:3000

### 5. 访问系统

1. 打开浏览器访问 http://localhost:3000
2. 注册账号并登录
3. 添加FTP服务器（默认内置服务器：127.0.0.1:2121，账号admin/admin123）
4. 创建同步任务，指定本地文件夹
5. 启动任务，开始自动同步

## 项目结构

```
qimo2/
├── backend/
│   ├── app.py              # Flask主应用
│   ├── auth.py             # 认证模块
│   ├── database.py         # 数据库初始化
│   ├── ftp_server.py       # FTP服务器（单例模式）
│   ├── ftp_routes.py       # FTP管理API
│   ├── sync_engine.py      # 同步引擎（策略模式+工厂模式）
│   ├── sync_routes.py      # 同步任务API
│   ├── watcher.py          # 文件监控（观察者模式）
│   ├── scheduler.py        # 定时扫描
│   ├── history_routes.py   # 历史记录API
│   ├── files_routes.py     # 文件浏览API
│   ├── requirements.txt    # Python依赖
│   └── data/               # 数据库文件
├── frontend/
│   ├── src/
│   │   ├── api/            # API接口
│   │   ├── router/         # 路由配置
│   │   ├── views/          # 页面组件
│   │   │   ├── Login.vue   # 登录页
│   │   │   ├── Layout.vue  # 布局框架
│   │   │   ├── Dashboard.vue # 控制面板
│   │   │   ├── Servers.vue # FTP服务器管理
│   │   │   ├── Tasks.vue   # 同步任务管理
│   │   │   ├── Files.vue   # 文件浏览
│   │   │   └── History.vue # 同步历史
│   │   ├── App.vue
│   │   └── main.js
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## API接口

### 认证接口
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/profile` - 获取用户信息

### FTP服务器接口
- `GET /api/ftp/servers` - 获取服务器列表
- `POST /api/ftp/servers` - 添加服务器
- `DELETE /api/ftp/servers/:id` - 删除服务器
- `POST /api/ftp/servers/:id/test` - 测试连接
- `GET /api/ftp/servers/:id/files` - 浏览远程文件

### 同步任务接口
- `GET /api/sync/tasks` - 获取任务列表
- `POST /api/sync/tasks` - 创建任务
- `DELETE /api/sync/tasks/:id` - 删除任务
- `POST /api/sync/tasks/:id/start` - 启动任务
- `POST /api/sync/tasks/:id/stop` - 停止任务
- `POST /api/sync/tasks/:id/sync` - 手动同步
- `GET /api/sync/tasks/:id/ignore` - 获取忽略规则
- `POST /api/sync/tasks/:id/ignore` - 添加忽略规则
- `DELETE /api/sync/tasks/:id/ignore/:ruleId` - 删除忽略规则

### 历史记录接口
- `GET /api/history/:taskId` - 获取任务历史
- `GET /api/history/all` - 获取所有历史
- `GET /api/history/stats` - 获取统计信息

### 文件浏览接口
- `GET /api/files/local` - 浏览本地文件

## 使用说明

### 添加FTP服务器
1. 点击"FTP服务器"菜单
2. 点击"添加服务器"按钮
3. 填写服务器信息（名称、地址、端口、用户名、密码）
4. 点击"测试连接"验证配置
5. 保存

### 创建同步任务
1. 点击"同步任务"菜单
2. 点击"创建任务"按钮
3. 选择FTP服务器
4. 填写本地同步路径（如：D:\my_sync_folder）
5. 选择同步策略
6. 设置扫描间隔
7. 点击"创建"

### 设置忽略规则
1. 在同步任务列表中，点击"忽略列表"
2. 输入匹配规则（如：*.svn、*.git、node_modules）
3. 点击"添加"

### 查看同步历史
1. 点击"同步历史"菜单
2. 可按任务筛选
3. 查看同步详情（时间、文件、方向、状态）

## 注意事项

1. 内置FTP服务器默认端口为2121，避免与系统21端口冲突
2. 本地同步路径需要有读写权限
3. 建议设置合理的扫描间隔（默认60秒），避免频繁扫描
4. 大文件同步可能需要较长时间，请耐心等待
5. 如遇连接问题，请检查防火墙设置

## 常见问题

**Q: 如何修改FTP服务器端口？**
A: 在 `backend/ftp_server.py` 中修改 `start` 方法的 `port` 参数。

**Q: 如何添加更多同步策略？**
A: 在 `backend/sync_engine.py` 中继承 `SyncStrategy` 类，实现新策略，然后注册到 `STRATEGIES` 字典。

**Q: 同步历史数据存储在哪里？**
A: 存储在 `backend/data/sync.db` SQLite数据库中。

## 许可证

本项目仅供学习使用。
