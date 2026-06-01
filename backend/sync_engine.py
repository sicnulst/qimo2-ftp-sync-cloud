"""
同步引擎模块
实现文件比对、同步策略、忽略列表、快照防死循环
策略模式：4种同步策略
工厂模式：创建同步任务
"""
import os
import hashlib
import time
import fnmatch
from abc import ABC, abstractmethod
from datetime import datetime
from ftplib import FTP, all_errors
from database import get_db
from path_utils import normalize_path


# ========== 策略模式：同步策略 ==========

class SyncStrategy(ABC):
    """同步策略基类"""
    
    @abstractmethod
    def should_sync(self, local_info, remote_info, snapshot_info):
        """判断是否需要同步（新增snapshot_info参数）"""
        pass
    
    @abstractmethod
    def get_direction(self, local_info, remote_info):
        """获取同步方向：local_to_remote / remote_to_local / skip"""
        pass


class NewestStrategy(SyncStrategy):
    """以最新文件为准（修复版：支持快照比对 + 尊重用户删除）"""
    
    def should_sync(self, local_info, remote_info, snapshot_info):
        if local_info is None and remote_info is None:
            return False
        # 关键修复：如果文件之前同步过（有快照）但现在只有一端有，
        # 说明用户主动删除了某一端的文件 → 尊重删除，不同步回来
        if snapshot_info and (local_info is None or remote_info is None):
            return False
        # 新文件（没有快照）且只有一端有 → 需要同步
        if local_info is None or remote_info is None:
            return True
        # 两端都有：用快照判断是否真的变了
        if snapshot_info:
            local_changed = (
                local_info.get('size') != snapshot_info.get('local_size') or
                local_info.get('mtime') != snapshot_info.get('local_mtime')
            )
            remote_changed = (
                remote_info.get('size') != snapshot_info.get('remote_size')
            )
            if not local_changed and not remote_changed:
                return False
            return True
        # 没有快照，用传统方式比较
        if local_info.get('mtime') is not None and remote_info.get('mtime') is not None:
            return local_info['mtime'] != remote_info['mtime']
        return local_info.get('size') != remote_info.get('size')
    
    def get_direction(self, local_info, remote_info):
        if local_info is None:
            return 'remote_to_local'
        if remote_info is None:
            return 'local_to_remote'
        # 关键修复：比较两端的mtime
        local_mtime = local_info.get('mtime')
        remote_mtime = remote_info.get('mtime')
        # 如果远端mtime可用，做真正的比较
        if local_mtime is not None and remote_mtime is not None:
            if local_mtime > remote_mtime:
                return 'local_to_remote'
            elif remote_mtime > local_mtime:
                return 'remote_to_local'
            else:
                return 'skip'
        # mtime不可用时，比较size：谁大说明谁被改过
        local_size = local_info.get('size', 0)
        remote_size = remote_info.get('size', 0)
        if local_size != remote_size:
            return 'local_to_remote' if local_size > remote_size else 'remote_to_local'
        return 'skip'


class SizeStrategy(SyncStrategy):
    """以文件大小为准（修复版：支持快照 + 尊重删除）"""
    
    def should_sync(self, local_info, remote_info, snapshot_info):
        if local_info is None and remote_info is None:
            return False
        # 尊重用户删除：有快照但只有一端有 → 不同步
        if snapshot_info and (local_info is None or remote_info is None):
            return False
        if local_info is None or remote_info is None:
            return True
        if snapshot_info:
            local_changed = local_info.get('size') != snapshot_info.get('local_size')
            remote_changed = remote_info.get('size') != snapshot_info.get('remote_size')
            if not local_changed and not remote_changed:
                return False
            return True
        return local_info.get('size') != remote_info.get('size')
    
    def get_direction(self, local_info, remote_info):
        if local_info is None:
            return 'remote_to_local'
        if remote_info is None:
            return 'local_to_remote'
        if local_info.get('size') != remote_info.get('size'):
            # 优先比较mtime（如果两端都可用）
            local_mtime = local_info.get('mtime')
            remote_mtime = remote_info.get('mtime')
            if local_mtime is not None and remote_mtime is not None:
                return 'local_to_remote' if local_mtime > remote_mtime else 'remote_to_local'
            # mtime不可用时，大小优先：谁大用谁的
            local_size = local_info.get('size', 0)
            remote_size = remote_info.get('size', 0)
            return 'local_to_remote' if local_size > remote_size else 'remote_to_local'
        return 'skip'


class ForceLocalStrategy(SyncStrategy):
    """强制以本地为准"""
    
    def should_sync(self, local_info, remote_info, snapshot_info):
        # 本地有文件就同步，不需要判断是否变化
        return local_info is not None
    
    def get_direction(self, local_info, remote_info):
        return 'local_to_remote'


class ForceRemoteStrategy(SyncStrategy):
    """强制以服务器为准"""
    
    def should_sync(self, local_info, remote_info, snapshot_info):
        # 云端有文件就同步，不需要判断是否变化
        return remote_info is not None
    
    def get_direction(self, local_info, remote_info):
        return 'remote_to_local'


# 策略工厂
STRATEGIES = {
    'newest': NewestStrategy,
    'size': SizeStrategy,
    'force_local': ForceLocalStrategy,
    'force_remote': ForceRemoteStrategy
}


def get_strategy(name):
    """获取同步策略实例"""
    strategy_class = STRATEGIES.get(name, NewestStrategy)
    return strategy_class()


# ========== 工厂模式：同步任务 ==========

class SyncTaskFactory:
    """同步任务工厂"""
    
    @staticmethod
    def create_task(task_config):
        """创建同步任务实例"""
        return SyncTask(task_config)


class SyncTask:
    """同步任务"""
    
    def __init__(self, config):
        self.task_id = config['id']
        self.local_path = normalize_path(config['local_path'])
        self.remote_path = config.get('remote_path', '/')
        self.strategy = get_strategy(config.get('sync_strategy', 'newest'))
        self.force_direction = config.get('force_direction', 'none')
        self.delete_sync = config.get('delete_sync', False)
        self.ignore_rules = config.get('ignore_rules', [])
        self.ftp_config = config.get('ftp_config', {})
    
    def is_ignored(self, path):
        """检查文件是否在忽略列表中（含全局默认规则）"""
        filename = os.path.basename(path)
        for pattern in SyncEngine.DEFAULT_IGNORE_PATTERNS:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(path, pattern):
                return True
        for rule in self.ignore_rules:
            pattern = rule['pattern']
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(path, pattern):
                return True
        return False


# ========== 同步引擎 ==========

class SyncEngine:
    """同步引擎核心（含快照防死循环）"""
    
    # 全局默认忽略规则
    DEFAULT_IGNORE_PATTERNS = [
        '~$*',          # Office临时文件
        '.~*',          # LibreOffice临时文件
        'Thumbs.db',    # Windows缩略图缓存
        'desktop.ini',  # Windows桌面配置
        '.DS_Store',    # macOS元数据
        '*.pyc',        # Python编译缓存
        '__pycache__',  # Python缓存目录
        '*.swp',        # Vim交换文件
        '*.tmp',        # 临时文件
    ]
    
    def create_ftp_connection(self, config):
        """创建新的FTP连接"""
        ftp = FTP()
        ftp.connect(config['host'], int(config['port']), timeout=30)
        username = config.get('username', 'anonymous')
        password = config.get('password', '')
        ftp.login(username, password)
        ftp.set_pasv(True)
        return ftp
    
    def _get_snapshots(self, task_id):
        """获取任务的同步快照"""
        snapshots = {}
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT file_path, local_size, local_mtime, remote_size FROM sync_snapshots WHERE sync_task_id = ?',
                (task_id,)
            )
            for row in cursor.fetchall():
                snapshots[row['file_path']] = dict(row)
            conn.close()
        except Exception:
            pass
        return snapshots
    
    def _save_snapshot(self, task_id, file_path, local_size, local_mtime, remote_size):
        """保存/更新单个文件的同步快照"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sync_snapshots (sync_task_id, file_path, local_size, local_mtime, remote_size, last_sync_time)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(sync_task_id, file_path) DO UPDATE SET
                    local_size = excluded.local_size,
                    local_mtime = excluded.local_mtime,
                    remote_size = excluded.remote_size,
                    last_sync_time = excluded.last_sync_time
            ''', (task_id, file_path, local_size, local_mtime, remote_size, datetime.now()))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[快照] 保存失败 {file_path}: {e}")
    
    def _remove_snapshot(self, task_id, file_path):
        """删除快照记录"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM sync_snapshots WHERE sync_task_id = ? AND file_path = ?',
                (task_id, file_path)
            )
            conn.commit()
            conn.close()
        except Exception:
            pass
    
    def scan_local(self, local_path, ignore_rules=None):
        """扫描本地文件"""
        files = {}
        if not os.path.exists(local_path):
            return files
        for root, dirs, filenames in os.walk(local_path):
            for name in filenames:
                full_path = os.path.join(root, name)
                rel_path = os.path.relpath(full_path, local_path)
                if self._is_ignored(rel_path, ignore_rules or []):
                    continue
                try:
                    stat = os.stat(full_path)
                    files[rel_path] = {
                        'path': full_path,
                        'size': stat.st_size,
                        'mtime': stat.st_mtime
                    }
                except:
                    pass
        return files
    
    def scan_remote(self, ftp, remote_path, ignore_rules=None):
        """扫描远程文件"""
        files = {}
        try:
            ftp.cwd(remote_path)
        except:
            try:
                ftp.mkd(remote_path)
                ftp.cwd(remote_path)
            except:
                return files
        self._scan_remote_dir(ftp, remote_path, '', files, ignore_rules)
        return files
    
    def _scan_remote_dir(self, ftp, base_path, current_path, files, ignore_rules):
        """递归扫描远程目录"""
        full_path = f"{base_path.rstrip('/')}/{current_path}".rstrip('/')
        if not full_path:
            full_path = '/'
        try:
            ftp.cwd(full_path)
        except:
            return
        entries = []
        ftp.retrlines('LIST', entries.append)
        for entry in entries:
            parts = entry.split(None, 8)
            if len(parts) < 9:
                continue
            is_dir = parts[0].startswith('d')
            size = int(parts[4]) if not is_dir else 0
            name = parts[8]
            if name in ('.', '..'):
                continue
            rel_path = f"{current_path}/{name}".lstrip('/')
            if self._is_ignored(rel_path, ignore_rules or []):
                continue
            if is_dir:
                self._scan_remote_dir(ftp, base_path, rel_path, files, ignore_rules)
            else:
                files[rel_path] = {
                    'size': size,
                    'mtime': None  # pyftpdlib不支持MDTM
                }
        try:
            ftp.cwd('..')
        except:
            pass
    
    def _is_ignored(self, path, ignore_rules):
        """检查是否匹配忽略规则"""
        filename = os.path.basename(path)
        for pattern in self.DEFAULT_IGNORE_PATTERNS:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(path, pattern):
                return True
        for rule in ignore_rules:
            pattern = rule['pattern']
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(path, pattern):
                return True
        return False
    
    def _detect_renames(self, task_id, local_files, remote_files, snapshots, direction='remote'):
        """检测重命名：一端消失的文件和另一端出现的新文件，如果大小相同则视为重命名
        
        返回: [(old_path, new_path), ...] 的重命名列表
        """
        renames = []
        
        if direction == 'remote':
            # 云端重命名：找出在云端消失但本地还有的文件（有快照）
            disappeared = {}  # size -> old_path
            for path, snap in snapshots.items():
                if path in local_files and path not in remote_files:
                    size = snap.get('remote_size') or snap.get('local_size')
                    if size is not None:
                        disappeared[size] = path
            
            # 找出在云端新出现的文件（没有快照，不在本地）
            appeared = {}  # size -> new_path
            for path, rinfo in remote_files.items():
                if path not in local_files and path not in snapshots:
                    size = rinfo.get('size')
                    if size is not None:
                        appeared.setdefault(size, []).append(path)
            
            # 按大小匹配
            for size, old_path in disappeared.items():
                if size in appeared and appeared[size]:
                    new_path = appeared[size].pop(0)
                    renames.append((old_path, new_path))
        
        elif direction == 'local':
            # 本地重命名：找出在本地消失但云端还有的文件
            disappeared = {}
            for path, snap in snapshots.items():
                if path in remote_files and path not in local_files:
                    size = snap.get('local_size') or snap.get('remote_size')
                    if size is not None:
                        disappeared[size] = path
            
            appeared = {}
            for path, linfo in local_files.items():
                if path not in remote_files and path not in snapshots:
                    size = linfo.get('size')
                    if size is not None:
                        appeared.setdefault(size, []).append(path)
            
            for size, old_path in disappeared.items():
                if size in appeared and appeared[size]:
                    new_path = appeared[size].pop(0)
                    renames.append((old_path, new_path))
        
        return renames

    def _apply_rename(self, ftp, task, old_path, new_path, direction):
        """执行重命名操作"""
        results = []
        
        if direction == 'remote':
            # 云端已改名，本地需要跟着改
            old_local = os.path.join(task.local_path, old_path)
            new_local = os.path.join(task.local_path, new_path)
            try:
                new_dir = os.path.dirname(new_local)
                os.makedirs(new_dir, exist_ok=True)
                os.rename(old_local, new_local)
                # 更新快照：删旧的，新的会在主循环里创建
                self._remove_snapshot(task.task_id, old_path)
                results.append({
                    'status': 'success',
                    'file': old_path,
                    'direction': 'remote_to_local',
                    'action': 'rename',
                    'new_file': new_path
                })
            except Exception as e:
                results.append({
                    'status': 'error',
                    'file': old_path,
                    'direction': 'remote_to_local',
                    'action': 'rename',
                    'error': str(e)
                })
        
        elif direction == 'local':
            # 本地已改名，云端需要跟着改
            old_remote = f"{task.remote_path.rstrip('/')}/{old_path}"
            new_remote = f"{task.remote_path.rstrip('/')}/{new_path}"
            try:
                new_dir = os.path.dirname(new_remote)
                self._ensure_remote_dir(ftp, new_dir)
                ftp.rename(old_remote, new_remote)
                self._remove_snapshot(task.task_id, old_path)
                results.append({
                    'status': 'success',
                    'file': old_path,
                    'direction': 'local_to_remote',
                    'action': 'rename',
                    'new_file': new_path
                })
            except Exception as e:
                results.append({
                    'status': 'error',
                    'file': old_path,
                    'direction': 'local_to_remote',
                    'action': 'rename',
                    'error': str(e)
                })
        
        return results

    def sync(self, task):
        """执行同步（含快照防死循环 + 重命名检测）"""
        results = []
        ftp = None
        try:
            ftp = self.create_ftp_connection(task.ftp_config)
            local_files = self.scan_local(task.local_path, task.ignore_rules)
            remote_files = self.scan_remote(ftp, task.remote_path, task.ignore_rules)
            
            # 获取上次同步快照
            snapshots = self._get_snapshots(task.task_id)
            
            # ====== 重命名检测（始终运行，改名≠删除） ======
            remote_renames = self._detect_renames(task.task_id, local_files, remote_files, snapshots, 'remote')
            for old_path, new_path in remote_renames:
                rename_results = self._apply_rename(ftp, task, old_path, new_path, 'remote')
                results.extend(rename_results)
                if old_path in snapshots:
                    del snapshots[old_path]
            
            local_renames = self._detect_renames(task.task_id, local_files, remote_files, snapshots, 'local')
            for old_path, new_path in local_renames:
                rename_results = self._apply_rename(ftp, task, old_path, new_path, 'local')
                results.extend(rename_results)
                if old_path in snapshots:
                    del snapshots[old_path]
            
            # 重命名后重新扫描（文件系统已变化）
            if remote_renames or local_renames:
                local_files = self.scan_local(task.local_path, task.ignore_rules)
                remote_files = self.scan_remote(ftp, task.remote_path, task.ignore_rules)
            
            # ====== 主同步循环 ======
            all_files = set(list(local_files.keys()) + list(remote_files.keys()))
            
            for rel_path in all_files:
                local_info = local_files.get(rel_path)
                remote_info = remote_files.get(rel_path)
                snapshot_info = snapshots.get(rel_path)
                
                # 用策略判断是否需要同步（传入快照）
                if not task.strategy.should_sync(local_info, remote_info, snapshot_info):
                    continue
                
                # 获取同步方向
                direction = task.strategy.get_direction(local_info, remote_info)
                
                # 应用强制方向
                if task.force_direction == 'local':
                    direction = 'local_to_remote'
                elif task.force_direction == 'remote':
                    direction = 'remote_to_local'
                
                if direction == 'skip':
                    continue
                
                # 跳过：源文件不存在
                if direction == 'local_to_remote' and local_info is None:
                    continue
                if direction == 'remote_to_local' and remote_info is None:
                    continue
                
                # 执行同步
                result = self._do_sync(ftp, task, rel_path, local_info, remote_info, direction)
                results.append(result)
                
                # 同步成功后更新快照
                if result.get('status') == 'success':
                    final_local = local_files.get(rel_path)
                    final_remote = remote_files.get(rel_path)
                    # 如果是下载，重新读取本地文件信息
                    if direction == 'remote_to_local':
                        local_file = os.path.join(task.local_path, rel_path)
                        try:
                            stat = os.stat(local_file)
                            final_local = {'size': stat.st_size, 'mtime': stat.st_mtime}
                        except:
                            final_local = None
                    
                    if final_local and final_remote:
                        self._save_snapshot(
                            task.task_id, rel_path,
                            final_local.get('size'), final_local.get('mtime'),
                            final_remote.get('size')
                        )
                    elif final_local:
                        self._save_snapshot(
                            task.task_id, rel_path,
                            final_local.get('size'), final_local.get('mtime'), None
                        )
            
            # 删除同步传播（扩展：所有策略都支持，不仅仅是force方向）
            if task.delete_sync:
                local_files_after = self.scan_local(task.local_path, task.ignore_rules)
                remote_files_after = self.scan_remote(ftp, task.remote_path, task.ignore_rules)
                
                if task.force_direction == 'local' or (task.delete_sync and task.force_direction == 'none'):
                    # 删除远端有但本地没有的文件（当delete_sync开启时）
                    for rel_path in list(remote_files_after.keys()):
                        if rel_path not in local_files_after:
                            remote_file = f"{task.remote_path.rstrip('/')}/{rel_path}"
                            try:
                                ftp.delete(remote_file)
                                results.append({
                                    'status': 'success',
                                    'file': rel_path,
                                    'direction': 'local_to_remote',
                                    'action': 'delete_remote'
                                })
                                self._remove_snapshot(task.task_id, rel_path)
                            except Exception as e:
                                results.append({
                                    'status': 'error',
                                    'file': rel_path,
                                    'direction': 'local_to_remote',
                                    'action': 'delete_remote',
                                    'error': str(e)
                                })
                
                if task.force_direction == 'remote' or (task.delete_sync and task.force_direction == 'none'):
                    for rel_path in list(local_files_after.keys()):
                        if rel_path not in remote_files_after:
                            local_file = os.path.join(task.local_path, rel_path)
                            try:
                                if os.path.exists(local_file):
                                    os.remove(local_file)
                                    results.append({
                                        'status': 'success',
                                        'file': rel_path,
                                        'direction': 'remote_to_local',
                                        'action': 'delete_local'
                                    })
                                    self._remove_snapshot(task.task_id, rel_path)
                            except Exception as e:
                                results.append({
                                    'status': 'error',
                                    'file': rel_path,
                                    'direction': 'remote_to_local',
                                    'action': 'delete_local',
                                    'error': str(e)
                                })
            
        except Exception as e:
            results.append({
                'status': 'error',
                'error': str(e)
            })
        finally:
            if ftp:
                try:
                    ftp.quit()
                except:
                    pass
        
        return results
    
    def _do_sync(self, ftp, task, rel_path, local_info, remote_info, direction):
        """执行单个文件同步"""
        local_file = os.path.join(task.local_path, rel_path)
        remote_file = f"{task.remote_path.rstrip('/')}/{rel_path}"
        action = 'unknown'
        
        if direction == 'local_to_remote':
            if remote_info is None:
                action = 'upload_new'
            else:
                action = 'upload_update'
            remote_dir = os.path.dirname(remote_file)
            self._ensure_remote_dir(ftp, remote_dir)
            with open(local_file, 'rb') as f:
                ftp.storbinary(f'STOR {remote_file}', f)
        
        elif direction == 'remote_to_local':
            if local_info is None:
                action = 'download_new'
            else:
                action = 'download_update'
            local_dir = os.path.dirname(local_file)
            os.makedirs(local_dir, exist_ok=True)
            with open(local_file, 'wb') as f:
                ftp.retrbinary(f'RETR {remote_file}', f.write)
        
        return {
            'status': 'success',
            'file': rel_path,
            'direction': direction,
            'action': action
        }
    
    def _ensure_remote_dir(self, ftp, path):
        """确保远程目录存在"""
        dirs = path.split('/')
        current = ''
        for d in dirs:
            if not d:
                continue
            current += f'/{d}'
            try:
                ftp.mkd(current)
            except:
                pass


# 全局同步引擎实例
sync_engine = SyncEngine()
