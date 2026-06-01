"""
定时扫描模块
使用APScheduler定时扫描本地文件夹
"""
import os
import threading
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from database import get_db
from sync_engine import sync_engine, SyncTaskFactory
from watcher import file_watcher
from path_utils import normalize_path


class ScanScheduler:
    """定时扫描调度器"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.scheduler = BackgroundScheduler()
                cls._instance.jobs = {}
                cls._instance.scheduler.start()
            return cls._instance
    
    def add_job(self, task_id, interval_seconds=60):
        """添加定时扫描任务"""
        if task_id in self.jobs:
            self.remove_job(task_id)
        
        job = self.scheduler.add_job(
            self._scan_and_sync,
            trigger=IntervalTrigger(seconds=interval_seconds),
            args=[task_id],
            id=f'scan_{task_id}',
            replace_existing=True
        )
        
        self.jobs[task_id] = {
            'job': job,
            'interval': interval_seconds
        }
        
        print(f"[调度器] 添加任务{task_id}，间隔{interval_seconds}秒")
        return True
    
    def remove_job(self, task_id):
        """移除定时任务"""
        if task_id in self.jobs:
            self.scheduler.remove_job(f'scan_{task_id}')
            del self.jobs[task_id]
            print(f"[调度器] 移除任务{task_id}")
            return True
        return False
    
    def _scan_and_sync(self, task_id):
        """执行扫描和同步"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # 获取任务配置
            cursor.execute('''
                SELECT st.*, fs.host, fs.port, fs.username, fs.password
                FROM sync_tasks st
                JOIN ftp_servers fs ON st.ftp_server_id = fs.id
                WHERE st.id = ? AND st.is_active = 1
            ''', (task_id,))
            task_row = cursor.fetchone()
            
            if not task_row:
                conn.close()
                return
            
            task_config = dict(task_row)
            task_config['local_path'] = normalize_path(task_config['local_path'])
            
            # 获取忽略规则
            cursor.execute('SELECT pattern FROM ignore_rules WHERE sync_task_id = ?', (task_id,))
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
            results = sync_engine.sync(task)
            
            # 保存历史
            self._save_history(task_id, results)
            
            print(f"[调度器] 任务{task_id}定时扫描完成，处理{len(results)}个文件")
            
        except Exception as e:
            print(f"[调度器] 任务{task_id}扫描失败: {e}")
    
    def _save_history(self, task_id, results):
        """保存同步历史"""
        conn = get_db()
        cursor = conn.cursor()
        
        for result in results:
            if result.get('file'):
                # 清理路径：去掉内部 user_*/ 前缀
                clean_path = result['file']
                if clean_path.startswith('user_'):
                    parts = clean_path.split('/', 2)
                    if len(parts) >= 3:
                        clean_path = parts[2]
                
                cursor.execute('''
                    INSERT INTO sync_history (sync_task_id, file_name, file_path, direction, action, status, error_message, sync_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task_id,
                    os.path.basename(clean_path),
                    clean_path,
                    result.get('direction', 'unknown'),
                    result.get('action', 'unknown'),
                    result.get('status', 'unknown'),
                    result.get('error'),
                    datetime.now(CST).isoformat()
                ))
        
        cursor.execute('UPDATE sync_tasks SET last_sync_time = ? WHERE id = ?', 
                       (datetime.now(CST).isoformat(), task_id))
        conn.commit()
        conn.close()
    
    def get_status(self):
        """获取所有任务状态"""
        status = {}
        for task_id, info in self.jobs.items():
            status[task_id] = {
                'interval': info['interval'],
                'next_run': str(info['job'].next_run_time)
            }
        return status
    
    def shutdown(self):
        """关闭调度器"""
        self.scheduler.shutdown()


# 全局调度器实例
scan_scheduler = ScanScheduler()
