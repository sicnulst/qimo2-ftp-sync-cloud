#!/usr/bin/env python3
"""
FTP同步云盘系统 - 自动化测试脚本
修完bug后跑一遍确认无回归
"""
import sys
import os
import time
import json
import requests

BASE = "http://127.0.0.1:5000"
TOKEN = None
PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} {detail}")


def api(method, path, **kwargs):
    headers = kwargs.pop("headers", {})
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    try:
        r = getattr(requests, method)(f"{BASE}{path}", headers=headers, timeout=10, **kwargs)
        return r
    except Exception as e:
        return None


# ========== 单元测试（直接导入引擎逻辑） ==========
def unit_tests():
    print("\n===== 单元测试 =====")
    sys.path.insert(0, os.path.dirname(__file__))

    from sync_engine import SyncEngine, SyncTaskFactory
    from path_utils import normalize_path, is_windows_path, is_wsl

    engine = SyncEngine()

    # 全局忽略规则
    print("1. 全局忽略规则")
    test("~$文件被忽略", engine._is_ignored("~$report.doc", []))
    test("Thumbs.db被忽略", engine._is_ignored("Thumbs.db", []))
    test(".pyc被忽略", engine._is_ignored("test.pyc", []))
    test("__pycache__被忽略", engine._is_ignored("__pycache__", []))
    test(".tmp被忽略", engine._is_ignored("cache.tmp", []))
    test("正常文件不被忽略", not engine._is_ignored("normal.txt", []))
    test("正常Python文件不被忽略", not engine._is_ignored("main.py", []))

    # 用户自定义规则
    print("2. 用户自定义忽略规则")
    rules = [{"pattern": "*.svn"}, {"pattern": "node_modules"}]
    test("*.svn被忽略", engine._is_ignored("test.svn", rules))
    test("node_modules被忽略", engine._is_ignored("node_modules", rules))
    test("同时检查默认+用户规则", engine._is_ignored("~$test.doc", rules))
    test("正常文件不被忽略", not engine._is_ignored("index.js", rules))

    # SyncTask.is_ignored
    print("3. SyncTask忽略检查")
    task = SyncTaskFactory.create_task({"id": 1, "local_path": "/tmp", "ignore_rules": []})
    test("空规则时~$仍被忽略", task.is_ignored("~$test.doc"))
    test("空规则时Thumbs.db仍被忽略", task.is_ignored("Thumbs.db"))

    # 路径转换
    print("4. 路径转换")
    test("Windows路径识别", is_windows_path("C:\\Users\\test"))
    test("Windows路径识别(正斜杠)", is_windows_path("C:/Users/test"))
    test("非Windows路径", not is_windows_path("/home/user"))
    test("路径转换C→/mnt/c", normalize_path("C:\\Users\\test") == "/mnt/c/Users/test" or not is_wsl())

    # 同步策略
    print("5. 同步策略")
    from sync_engine import NewestStrategy, SizeStrategy, ForceLocalStrategy, ForceRemoteStrategy

    newest = NewestStrategy()
    test("新文件需要同步", newest.should_sync(None, {"size": 100, "mtime": 1}))
    test("新文件方向:remote→local", newest.get_direction(None, {"size": 100, "mtime": 1}) == "remote_to_local")
    test("本地新文件方向:local→remote", newest.get_direction({"size": 100, "mtime": 2}, None) == "local_to_remote")

    force_local = ForceLocalStrategy()
    test("强制本地:始终同步", force_local.should_sync(None, None))
    test("强制本地:方向local→remote", force_local.get_direction(None, None) == "local_to_remote")

    force_remote = ForceRemoteStrategy()
    test("强制远程:始终同步", force_remote.should_sync(None, None))
    test("强制远程:方向remote→local", force_remote.get_direction(None, None) == "remote_to_local")


# ========== API集成测试 ==========
def api_tests():
    global TOKEN
    print("\n===== API集成测试 =====")

    # 健康检查
    r = api("get", "/api/health")
    test("健康检查", r and r.status_code == 200)

    # 登录
    r = api("post", "/api/auth/login", json={"username": "testuser", "password": "test123456"})
    test("登录", r and r.status_code == 200)
    if r and r.status_code == 200:
        TOKEN = r.json().get("access_token")
    test("获取Token", TOKEN is not None)

    # 用户信息
    r = api("get", "/api/auth/profile")
    test("获取用户信息", r and r.status_code == 200)

    # FTP服务器
    r = api("get", "/api/ftp/servers")
    test("服务器列表", r and r.status_code == 200)

    r = api("post", "/api/ftp/servers/1/test")
    test("FTP连接测试", r and r.status_code == 200 and r.json().get("status") == "success")

    # FTP内置服务器
    r = api("get", "/api/ftp/builtin/status")
    test("FTP状态", r and r.status_code == 200 and r.json().get("is_running"))

    # 同步任务CRUD
    test_dir = "/tmp/auto_test_sync"
    os.makedirs(test_dir, exist_ok=True)
    with open(f"{test_dir}/test.txt", "w") as f:
        f.write("test content")

    r = api("post", "/api/sync/tasks", json={
        "ftp_server_id": 1,
        "local_path": test_dir,
        "remote_path": "/auto_test",
        "sync_strategy": "newest",
        "auto_sync": False
    })
    test("创建同步任务", r and r.status_code == 201)

    r = api("get", "/api/sync/tasks")
    test("任务列表", r and r.status_code == 200 and len(r.json().get("tasks", [])) > 0)

    # 手动同步
    tasks = r.json()["tasks"]
    tid = None
    for t in tasks:
        if "auto_test_sync" in t.get("local_path", ""):
            tid = t["id"]
            break
    test("找到测试任务", tid is not None)

    if tid:
        r = api("post", f"/api/sync/tasks/{tid}/sync")
        test("手动同步", r and r.status_code == 200 and r.json().get("synced_count", 0) > 0)

        # 忽略规则
        r = api("post", f"/api/sync/tasks/{tid}/ignore", json={"pattern": "*.log"})
        test("添加忽略规则", r and r.status_code == 201)

        r = api("get", f"/api/sync/tasks/{tid}/ignore")
        test("获取忽略规则", r and r.status_code == 200 and len(r.json().get("rules", [])) > 0)

        # 任务控制
        r = api("post", f"/api/sync/tasks/{tid}/pause")
        test("暂停任务", r and r.status_code == 200)

        r = api("post", f"/api/sync/tasks/{tid}/start")
        test("启动任务", r and r.status_code == 200)

        # 清理
        r = api("post", f"/api/sync/tasks/{tid}/stop")
        r = api("delete", f"/api/sync/tasks/{tid}")
        test("删除任务", r and r.status_code == 200)

    # 历史记录
    r = api("get", "/api/history/stats")
    test("同步统计", r and r.status_code == 200 and "total" in r.json())

    r = api("get", "/api/history/all?page=1")
    test("同步历史", r and r.status_code == 200 and "history" in r.json())

    # 文件浏览
    r = api("get", "/api/files/local", params={"path": test_dir, "subpath": "/"})
    test("本地文件浏览", r and r.status_code == 200 and "files" in r.json())

    # 监控/调度器状态
    r = api("get", "/api/sync/watcher/status")
    test("监控器状态", r and r.status_code == 200)

    r = api("get", "/api/sync/scheduler/status")
    test("调度器状态", r and r.status_code == 200)

    # 清理
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)
    r = api("get", "/api/ftp/servers")
    if r:
        for s in r.json().get("servers", []):
            if s["id"] != 1:
                api("delete", f"/api/ftp/servers/{s['id']}")


if __name__ == "__main__":
    print("FTP同步云盘系统 - 自动化测试")
    print("=" * 40)

    unit_tests()
    api_tests()

    print(f"\n{'=' * 40}")
    print(f"结果: {PASS} 通过, {FAIL} 失败")
    if FAIL > 0:
        print("⚠️  有失败项，请检查！")
        sys.exit(1)
    else:
        print("✅ 全部通过")
        sys.exit(0)
