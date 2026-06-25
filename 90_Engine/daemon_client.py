"""90_Engine/daemon_client.py — vault 데몬 디스커버리 + 경량 HTTP 클라이언트.

mcp_server(프록시)와 vault_daemon이 **같은 포트 계산**을 쓰도록 공유한다. 무거운 의존성
(fastapi/uvicorn) 없이 stdlib만 사용하므로 프록시 import 비용이 작다. See docs/DAEMON_DESIGN.md.
"""
import os
import sys
import json
import time
import hashlib
import subprocess
import urllib.request
from pathlib import Path


def daemon_port(vault_db) -> int:
    """vault DB 경로 기반 결정적 포트. hash()는 프로세스마다 salt가 달라 쓰면 안 되므로
    hashlib로 계산 → 프록시와 데몬이 동일 포트에 합의한다."""
    env = os.environ.get("DAEMON_PORT")
    if env:
        return int(env)
    h = int(hashlib.md5(str(Path(vault_db).resolve()).encode("utf-8")).hexdigest(), 16)
    return 40000 + (h % 2000)


def base(port: int) -> str:
    return f"http://127.0.0.1:{port}"


def health(port: int, timeout: float = 1.0):
    """데몬 /health 응답(dict) 또는 None."""
    try:
        with urllib.request.urlopen(base(port) + "/health", timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def get(port: int, path: str, timeout: float = 30.0):
    with urllib.request.urlopen(base(port) + path, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def post(port: int, path: str, payload: dict, timeout: float = 120.0):
    req = urllib.request.Request(
        base(port) + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def ensure_daemon(vault_db, script_dir, env=None, wait: float = 20.0):
    """데몬이 떠 있으면 port 반환. 아니면 detached로 기동하고 /health ready까지 폴링.
    실패하면 None(프록시는 read 직접 폴백 / write 에러)."""
    port = daemon_port(vault_db)
    if health(port):
        return port
    script = str(Path(script_dir) / "vault_daemon.py")
    kwargs = dict(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                  env=env or os.environ, close_fds=True)
    if os.name == "nt":  # Windows: 부모와 분리된 자식
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:  # POSIX: 새 세션으로 분리
        kwargs["start_new_session"] = True
    try:
        subprocess.Popen([sys.executable, script], **kwargs)
    except Exception:
        return None
    deadline = time.time() + wait
    while time.time() < deadline:
        if health(port):
            return port
        time.sleep(0.3)
    return None
