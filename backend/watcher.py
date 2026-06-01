"""
文件监控模块
使用watchdog监控本地文件变化，自动触发同步
观察者模式：watchdog本身就是观察者模式的实现
"""
import os
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime, timezone, timedelta

# 中国时区
CST = timezone(timedelta(hours=8))
from database import get_db
from sync_engine import sync_engine, SyncTaskFactory
from path_utils import normalize_path


class SyncEventHandler(FileSystemEventHandler):
    """文件同步事件处理器"""
    
    # 不需要触发同步的文件扩展名
    IGNORED_EXTENSIONS = {'.pyc', '.pyo', '.tmp', '.swp', '.bak', '.log', '~'}
    # 不需要触发同步的文件名前缀（临时文件）
    IGNORED_PREFIXES = ('.', '~')
    
    def __init__(self, task_id, sync_engine):
        super().__init__()
        self.task_id = task_id
        self.engine = sync_engine
        self.pending_sync = False
        self.sync_timer = None
        self.debounce_seconds = 2
    
    def _should_ignore_event(self, path):
        """判断是否应该忽略此文件的事件"""
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lower()
        if ext in self.IGNORED_EXTENSIONS:
            return True
        if name.startswith(self.IGNORED_PREFIXES):
            return True
        return False
    
    def _schedule_sync(self):
        """延迟同步（防抖动）"""
        if self.sync_timer:
            self.sync_timer.cancel()
        self.sync_timer = threading.Timer(self.debounce_seconds, self._do_sync)
        self.sync_timer.start()
    
    def _do_sync(self):
        """执行同步"""
        try:
            # 从数据库获取任务配置
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT st.*, fs.host, fs.port, fs.username, fs.password, fs.remote_path as server_remote_path
                FROM sync_tasks st
                JOIN ftp_servers fs ON st.ftp_server_id = fs.id
                WHERE st.id = ?
            ''', (self.task_id,))
            task_row = cursor.fetchone()
            
            if not task_row:
                conn.close()
                return
            
            task_config = dict(task_row)
            task_config['local_path'] = normalize_path(task_config['local_path'])
            
            # 获取忽略规则
            cursor.execute('SELECT pattern FROM ignore_rules WHERE sync_task_id = ?', (self.task_id,))
            task_config['ignore_rules'] = [{'pattern': row['pattern']} for row in cursor.fetchall()]
            
            # FTP配置
            task_config['ftp_config'] = {
                'host': task_config['host'],
                'port': task_config['port'],
                'username': task_config['username'],
                'password': task_config['password']
            }
            
            conn.close()
            
            # 创建任务并执行同步
            task = SyncTaskFactory.create_task(task_config)
            results = self.engine.sync(task)
            
            # 记录同步历史
            self._save_history(results)
            
            print(f"[任务{self.task_id}] 同步完成，处理 {len(results)} 个文件")
            
        except Exception as e:
            print(f"[任务{self.task_id}] 同步失败: {e}")
    
    def _save_history(self, results):
        """保存同步历史"""
        conn = get_db()
        cursor = conn.cursor()
        
        for result in results:
            if result.get('file'):
                # 清理路径：去掉内部 user_*/ 前缀，只保留相对路径
                clean_path = result['file']
                if clean_path.startswith('user_'):
                    parts = clean_path.split('/', 2)
                    if len(parts) >= 3:
                        clean_path = parts[2]  # user_id/server_name/real_path
                
                cursor.execute('''
                    INSERT INTO sync_history (sync_task_id, file_name, file_path, direction, action, status, error_message, sync_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.task_id,
                    os.path.basename(clean_path),
                    clean_path,
                    result.get('direction', 'unknown'),
                    result.get('action', 'unknown'),
                    result.get('status', 'unknown'),
                    result.get('error'),
                    datetime.now(CST).isoformat()
                ))
        
        # 更新最后同步时间
        cursor.execute('UPDATE sync_tasks SET last_sync_time = ? WHERE id = ?', 
                       (datetime.now(CST).isoformat(), self.task_id))
        
        conn.commit()
        conn.close()
    
    def on_created(self, event):
        """文件创建事件"""
        if not event.is_directory and not self._should_ignore_event(event.src_path):
            print(f"[任务{self.task_id}] 检测到新文件: {event.src_path}")
            self._schedule_sync()
    
    def on_modified(self, event):
        """文件修改事件"""
        if not event.is_directory and not self._should_ignore_event(event.src_path):
            print(f"[任务{self.task_id}] 检测到文件修改: {event.src_path}")
            self._schedule_sync()
    
    def on_deleted(self, event):
        """文件删除事件"""
        if not event.is_directory and not self._should_ignore_event(event.src_path):
            print(f"[任务{self.task_id}] 检测到文件删除: {event.src_path}")
            self._schedule_sync()
    
    def on_moved(self, event):
        """文件移动事件"""
        if not event.is_directory and not self._should_ignore_event(event.src_path):
            print(f"[任务{self.task_id}] 检测到文件移动: {event.src_path} -> {event.dest_path}")
            self._schedule_sync()


class FileWatcher:
    """文件监控器（观察者模式）"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.observers = {}
                cls._instance.running = False
            return cls._instance
    
    def start_watching(self, task_id, local_path):
        """开始监控目录"""
        if task_id in self.observers:
            self.stop_watching(task_id)
        
        if not os.path.exists(local_path):
            os.makedirs(local_path, exist_ok=True)
        
        handler = SyncEventHandler(task_id, sync_engine)
        observer = Observer()
        observer.schedule(handler, local_path, recursive=True)
        observer.start()
        
        self.observers[task_id] = {
            'observer': observer,
            'handler': handler,
            'path': local_path
        }
        
        print(f"[监控器] 开始监控任务{task_id}: {local_path}")
        return True
    
    def stop_watching(self, task_id):
        """停止监控"""
        if task_id in self.observers:
            info = self.observers[task_id]
            info['observer'].stop()
            info['observer'].join()
            del self.observers[task_id]
            print(f"[监控器] 停止监控任务{task_id}")
            return True
        return False
    
    def get_status(self):
        """获取所有监控状态"""
        status = {}
        for task_id, info in self.observers.items():
            status[task_id] = {
                'path': info['path'],
                'is_alive': info['observer'].is_alive()
            }
        return status
    
    def stop_all(self):
        """停止所有监控"""
        for task_id in list(self.observers.keys()):
            self.stop_watching(task_id)


# 全局监控器实例
file_watcher = FileWatcher()
