#!/usr/bin/env python3
"""90_Engine/vault_daemon.py — single-owner vault daemon (M1: read endpoints).

Why: the snapshot+os.replace concurrency model is POSIX-bound. A single owner
process per machine removes multi-process DuckDB file contention entirely and is
cross-platform. Thin `mcp_server.py` proxies forward tool calls here over
localhost HTTP. See docs/DAEMON_DESIGN.md.

M1 scope: read endpoints only (`/health`, `/retrieve`, `/vault_stats`) +
lifecycle (singleton via deterministic port + portfile, optional idle shutdown).
Writes still go through the proxy's in-process path until M2.

One daemon per machine per vault. Discovery: deterministic port from the vault
DB path (proxy and daemon compute the same port); liveness via /health.
"""
import os
import sys
import time
import signal
import threading
import contextlib
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
import retriever as retriever_mod  # noqa: E402
import indexer as indexer_mod  # noqa: E402
import daemon_client  # noqa: E402

# ── 환경 (프록시가 주입; mcp_server와 동일 키) ──
VAULT_ROOT = os.environ.get("VAULT_ROOT", str(SCRIPT_DIR.parent))
VAULT_DB = os.environ.get("VAULT_DB", str(SCRIPT_DIR / "ltm_cache.db"))
OLLAMA_URL = os.environ.get("OLLAMA_URL", retriever_mod.DEFAULT_OLLAMA_URL)
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", retriever_mod.DEFAULT_EMBED_MODEL)

# ── 옵션 (DAEMON_DESIGN.md §7) ──
_TRUE = ("1", "true", "on", "yes")
IDLE_SHUTDOWN = os.environ.get("DAEMON_IDLE_SHUTDOWN", "false").lower() in _TRUE  # 기본 상시가동


def _env_float(key, default):
    try:
        return float(os.environ.get(key, default))
    except (TypeError, ValueError):
        return float(default)


IDLE_TIMEOUT = _env_float("DAEMON_IDLE_TIMEOUT", 1800)  # 30분 (잘못된 값이면 기본값)

PORT = daemon_client.daemon_port(VAULT_DB)  # 프록시(mcp_server)와 동일 포트에 합의

# ── 단일 소유자 상태 (in-process 락으로 직렬화) ──
_lock = threading.RLock()
_retriever = None
_last_activity = time.time()


def _touch():
    global _last_activity
    _last_activity = time.time()


def get_retriever():
    """인메모리 그래프를 1회 적재해 보유(머신당 1회). double-checked: 적재 후엔 락 없이
    읽으므로 read가 동시 실행된다(락은 '빌드'만 보호). write 후 무효화는 M2에서."""
    global _retriever
    if _retriever is None:
        with _lock:
            if _retriever is None:
                if not Path(VAULT_DB).exists():
                    raise RuntimeError(
                        f"DuckDB 캐시가 없습니다: {VAULT_DB}\n"
                        f"먼저 'python3 indexer.py --embed --force' 실행 필요"
                    )
                _retriever = retriever_mod.Retriever(
                    VAULT_DB, OLLAMA_URL, OLLAMA_MODEL, vault_root=VAULT_ROOT
                )
    return _retriever


def invalidate_retriever():
    """write(reindex) 후 호출: 인메모리 그래프를 버려 다음 read가 새 DB로 재적재한다."""
    global _retriever
    with _lock:
        _retriever = None


# ── reader/writer 조정 ──
# DuckDB는 같은 프로세스에서 read-only/read-write 연결을 동시에 못 연다(probe로 확인).
# 따라서 다중 read는 동시 허용하되, write(reindex)는 배타(진행 중 read 연결이 0일 때만
# read-write로 연다). writer-preference로 writer 기아를 막는다.
class _RWLock:
    def __init__(self):
        self._c = threading.Condition()
        self._readers = 0
        self._writer = False
        self._writers_waiting = 0

    def acquire_read(self):
        with self._c:
            while self._writer or self._writers_waiting:
                self._c.wait()
            self._readers += 1

    def release_read(self):
        with self._c:
            self._readers -= 1
            if self._readers == 0:
                self._c.notify_all()

    def acquire_write(self):
        with self._c:
            self._writers_waiting += 1
            while self._writer or self._readers:
                self._c.wait()
            self._writers_waiting -= 1
            self._writer = True

    def release_write(self):
        with self._c:
            self._writer = False
            self._c.notify_all()


_rw = _RWLock()


@contextlib.contextmanager
def _read_lock():
    _rw.acquire_read()
    try:
        yield
    finally:
        _rw.release_read()


@contextlib.contextmanager
def _write_lock():
    _rw.acquire_write()
    try:
        yield
    finally:
        _rw.release_write()


# ── HTTP 앱 (FastAPI) ──
from fastapi import FastAPI, HTTPException          # noqa: E402
from pydantic import BaseModel                       # noqa: E402

app = FastAPI(title="llm-vault daemon")


class RetrieveReq(BaseModel):
    query: str
    top_k: int = 5
    max_hops: int = 2
    max_nodes: int = 10
    include_raw: bool = True
    include_reviews: bool = False
    confidence_weighting: bool = True


@app.get("/health")
def health():
    _touch()
    r = _retriever  # 락 없이 스냅샷(liveness probe라 racy해도 무해) — retrieve를 막지 않음
    loaded = r is not None
    n = len(r.nodes) if loaded else None
    return {
        "status": "ok",
        "pid": os.getpid(),
        "port": PORT,
        "db": str(VAULT_DB),
        "vault_root": str(VAULT_ROOT),
        "graph_loaded": loaded,
        "node_count": n,
        "idle_shutdown": IDLE_SHUTDOWN,
    }


@app.post("/retrieve")
def retrieve(req: RetrieveReq):
    _touch()
    try:
        with _read_lock():  # write(reindex)와 배타; reader끼리는 동시
            r = get_retriever()
            return r.retrieve(
                req.query, top_k=req.top_k, max_hops=req.max_hops,
                max_nodes=req.max_nodes, include_raw=req.include_raw,
                include_reviews=req.include_reviews,
                confidence_weighting=req.confidence_weighting,
            )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vault_stats")
def vault_stats():
    _touch()
    try:
        with _read_lock():
            return retriever_mod.compute_vault_stats(get_retriever(), OLLAMA_MODEL)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


class ReindexReq(BaseModel):
    force: bool = False
    embed: bool = True


@app.post("/reindex")
def reindex(req: ReindexReq):
    """write 경로: Markdown을 DuckDB로 증분 컴파일(in-place — 단일 소유자라 snapshot 불필요).
    배타 write 락 → 진행 중 read 연결이 0일 때만 read-write로 연다(DuckDB 동시-연결 제약)."""
    _touch()
    try:
        with _write_lock():
            try:
                with contextlib.redirect_stdout(sys.stderr):  # indexer 로그가 응답을 오염시키지 않게
                    stats, conn = indexer_mod.index_vault(
                        Path(VAULT_ROOT), Path(VAULT_DB),
                        force_rebuild=req.force, embed=req.embed,
                        ollama_url=OLLAMA_URL, embed_model=OLLAMA_MODEL,
                    )
                    conn.close()
            finally:
                # 부분 실패(in-place)에도 그래프 무효화 → 다음 read가 현재 디스크 상태로 재적재
                invalidate_retriever()
        return stats
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


# ── 라이프사이클: 싱글턴 · idle watchdog ──
def _existing_healthy(timeout=1.0) -> bool:
    h = daemon_client.health(PORT, timeout=timeout)
    return bool(h and h.get("status") == "ok")


def _idle_watchdog(server):
    while not getattr(server, "should_exit", False):
        time.sleep(15)
        if IDLE_SHUTDOWN and (time.time() - _last_activity) > IDLE_TIMEOUT:
            print(f"[daemon] idle {IDLE_TIMEOUT}s 초과 → 종료", file=sys.stderr)
            server.should_exit = True
            return


def main():
    # 싱글턴: 건강한 데몬이 이미 있으면 종료(중복 방지). 포트 바인드 경쟁은 uvicorn이 해소한다
    # (SO_REUSEADDR → 직전에 죽은 데몬의 TIME_WAIT 포트도 재바인드 가능; 경쟁에서 지면 즉시 반환).
    if _existing_healthy():
        print(f"[daemon] 이미 :{PORT}에서 동작 중 → 종료", file=sys.stderr)
        return

    import uvicorn
    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    # uvicorn 기본 시그널 핸들러 대신 우리 것 설치 → SIGTERM/SIGINT에 graceful 종료
    server.install_signal_handlers = lambda: None

    def _on_signal(_signum, _frame):
        server.should_exit = True
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    threading.Thread(target=_idle_watchdog, args=(server,), daemon=True).start()
    print(f"[daemon] llm-vault daemon up on http://127.0.0.1:{PORT} "
          f"(db={VAULT_DB}, idle_shutdown={IDLE_SHUTDOWN})", file=sys.stderr)
    server.run()


if __name__ == "__main__":
    main()
