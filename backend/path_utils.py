"""
路径工具模块
处理Windows路径与WSL路径的自动转换
"""
import os
import platform
import re


def is_wsl():
    """检测是否在WSL环境"""
    try:
        with open('/proc/version', 'r') as f:
            return 'microsoft' in f.read().lower()
    except:
        return False


def is_windows_path(path):
    """判断是否是Windows路径（如 C:\\Users 或 C:/Users）"""
    return bool(re.match(r'^[A-Za-z]:\\', path)) or bool(re.match(r'^[A-Za-z]:/', path))


def windows_to_wsl_path(win_path):
    """将Windows路径转为WSL路径
    C:\\Users\\20231\\Desktop -> /mnt/c/Users/20231/Desktop
    """
    # 统一用正斜杠
    p = win_path.replace('\\', '/')
    # 提取盘符
    match = re.match(r'^([A-Za-z]):/(.*)$', p)
    if match:
        drive = match.group(1).lower()
        rest = match.group(2)
        return f'/mnt/{drive}/{rest}'
    return win_path


def normalize_path(path):
    """根据运行环境自动转换路径
    - WSL下收到Windows路径 -> 转为 /mnt/... 路径
    - Windows下收到WSL路径 -> 不转换（保持原样）
    - 已经是正确的路径 -> 不转换
    """
    if not path:
        return path
    
    # 如果在WSL下收到了Windows路径
    if is_wsl() and is_windows_path(path):
        return windows_to_wsl_path(path)
    
    return path


# 缓存检测结果
_IS_WSL = None

def get_is_wsl():
    global _IS_WSL
    if _IS_WSL is None:
        _IS_WSL = is_wsl()
    return _IS_WSL
