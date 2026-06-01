"""
FTP服务器模块
使用pyftpdlib搭建本地miniFTP服务器
单例模式：确保只有一个FTP服务器实例运行
"""
import os
import socket
import threading
import subprocess
import time
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer


def is_port_in_use(port, host='127.0.0.1'):
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def kill_process_on_port(port):
    """杀掉占用端口的进程（跨平台）"""
    try:
        import platform
        if platform.system() == 'Windows':
            result = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True, text=True, shell=True
            )
            for line in result.stdout.split('\n'):
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    pid = parts[-1]
                    subprocess.run(['taskkill', '/F', '/PID', pid], shell=True, capture_output=True)
                    return True
        else:
            # Linux / macOS / WSL
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True, text=True
            )
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                pid = pid.strip()
                if pid:
                    subprocess.run(['kill', '-9', pid], capture_output=True)
                    return True
    except Exception:
        pass
    return False


class FTPServerManager:
    """FTP服务器管理器（单例模式）"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.server = None
                cls._instance.thread = None
                cls._instance.is_running = False
                cls._instance.ftp_root = None
                cls._instance.host = None
                cls._instance.port = None
                cls._instance.username = None
                cls._instance.password = None
            return cls._instance
    
    def start(self, host='127.0.0.1', port=2121, ftp_root=None, username='admin', password='admin123', force=False):
        """启动FTP服务器"""
        # 如果已在运行且不强制重启
        if self.is_running and not force:
            return {'status': 'already_running', 'host': self.host, 'port': self.port}
        
        # 如果强制重启，先停止
        if force:
            self.stop()
            kill_process_on_port(port)
            time.sleep(2)
        
        # 检查端口是否被占用
        if is_port_in_use(port, host):
            # 尝试连接现有服务器
            try:
                from ftplib import FTP
                ftp = FTP()
                ftp.connect(host, port, timeout=5)
                ftp.login(username, password)
                ftp.set_pasv(True)
                ftp.quit()
                self.is_running = True
                self.host = host
                self.port = port
                self.username = username
                self.password = password
                return {'status': 'already_running', 'host': host, 'port': port, 'note': '使用现有服务'}
            except Exception as e:
                # 无法连接，尝试杀掉进程重启
                kill_process_on_port(port)
                time.sleep(2)
        
        # 设置FTP根目录
        if ftp_root is None:
            ftp_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ftp_storage')
        self.ftp_root = ftp_root
        os.makedirs(ftp_root, exist_ok=True)
        
        # 创建授权器
        authorizer = DummyAuthorizer()
        authorizer.add_user(username, password, ftp_root, perm='elradfmw')
        authorizer.add_anonymous(ftp_root, perm='elradfmw')
        
        # 创建FTP处理器 - 关键配置
        handler = FTPHandler
        handler.authorizer = authorizer
        
        # 配置被动模式端口范围（兼容性更好）
        handler.passive_ports = range(50000, 50100)
        
        # 允许所有地址
        handler.permit_foreign_addresses = True
        handler.permit_privileged_ports = True
        
        # 设置编码
        handler.encoding = 'utf-8'
        
        # 创建服务器
        try:
            self.server = FTPServer((host, port), handler)
            self.server.max_cons = 256
            self.server.max_cons_per_ip = 10
            
            # 在新线程中启动
            self.thread = threading.Thread(target=self._run_server, daemon=True)
            self.thread.start()
            self.is_running = True
            self.host = host
            self.port = port
            self.username = username
            self.password = password
            
            print(f"FTP服务器已启动: {host}:{port}")
            print(f"FTP根目录: {ftp_root}")
            print(f"被动模式端口: 50000-50099")
            
            return {
                'status': 'started',
                'host': host,
                'port': port,
                'username': username,
                'password': password,
                'ftp_root': ftp_root
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _run_server(self):
        """运行FTP服务器"""
        try:
            self.server.serve_forever()
        except Exception as e:
            print(f"FTP服务器错误: {e}")
            self.is_running = False
    
    def stop(self):
        """停止FTP服务器"""
        if not self.is_running:
            return {'status': 'not_running'}
        
        if self.server:
            try:
                self.server.close_all()
            except:
                pass
        self.is_running = False
        self.server = None
        
        return {'status': 'stopped'}
    
    def restart(self, host='127.0.0.1', port=2121, username='admin', password='admin123'):
        """重启FTP服务器"""
        self.stop()
        time.sleep(1)
        return self.start(host=host, port=port, username=username, password=password, force=True)
    
    def get_status(self):
        """获取服务器状态"""
        return {
            'is_running': self.is_running,
            'host': self.host or '127.0.0.1',
            'port': self.port or 2121,
            'username': self.username or 'admin',
            'ftp_root': self.ftp_root
        }


# 全局单例
ftp_manager = FTPServerManager()
