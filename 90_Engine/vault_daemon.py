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
DB path + a portfile next to the DB.
"""
import os
import sys
import json
import time
import signal
import atexit
import threading
import urllib.request
from pathlib import Path
from collections import Counter

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
import retriever as retriever_mod  # noqa: E402
import daemon_client  # noqa: E402

# ── 환경 (프록시가 주입; mcp_server와 동일 키) ──
VAULT_ROOT = os.environ.get("VAULT_ROOT", str(SCRIPT_DIR.parent))
VAULT_DB = os.environ.get("VAULT_DB", str(SCRIPT_DIR / "ltm_cache.db"))
OLLAMA_URL = os.environ.get("OLLAMA_URL", retriever_mod.DEFAULT_OLLAMA_URL)
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", retriever_mod.DEFAULT_EMBED_MODEL)

# ── 옵션 (DAEMON_DESIGN.md §7) ──
_TRUE = ("1", "true", "on", "yes")
IDLE_SHUTDOWN = os.environ.get("DAEMON_IDLE_SHUTDOWN", "false").lower() in _TRUE  # 기본 상시가동
IDLE_TIMEOUT = float(os.environ.get("DAEMON_IDLE_TIMEOUT", "1800"))               # 30분


PORT = daemon_client.daemon_port(VAULT_DB)  # 프록시(mcp_server)와 동일 포트에 합의
PORTFILE = Path(str(VAULT_DB) + ".daemon.json")

# ── 단일 소유자 상태 (in-process 락으로 직렬화) ──
_lock = threading.RLock()
_retriever = None
_last_activity = time.time()


def _touch():
    global _last_activity
    _last_activity = time.time()


def get_retriever():
    """인메모리 그래프를 1회 적재해 보유(머신당 1회). write 후 무효화는 M2에서."""
    global _retriever
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
    global _retriever
    with _lock:
        _retriever = None


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
    with _lock:
        loaded = _retriever is not None
        n = len(_retriever.nodes) if loaded else None
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
        with _lock:
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
        with _lock:
            r = get_retriever()

            def _title(nid):
                n = r.nodes.get(str(nid))
                return n["title"] if n else str(nid)

            pred = Counter(e["predicate"] for e in r.edges)
            in_deg = Counter(_title(e["target_id"]) for e in r.edges)
            out_deg = Counter(_title(e["source_id"]) for e in r.edges)

            def _top5(c):
                return {t: d for t, d in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:5]}

            n_emb = sum(1 for n in r.nodes.values() if n["has_embedding"])
            return {
                "nodes_total": len(r.nodes),
                "edges_total": len(r.edges),
                "embedding_coverage": f"{n_emb}/{len(r.nodes)}",
                "embedding_model": OLLAMA_MODEL,
                "predicate_distribution": dict(pred.most_common()),
                "hub_top5_in_degree": _top5(in_deg),
                "authority_top5_out_degree": _top5(out_deg),
            }
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


# ── 라이프사이클: 싱글턴 · portfile · idle watchdog ──
def _existing_healthy(timeout=1.0) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8")).get("status") == "ok"
    except Exception:
        return False


def _write_portfile():
    try:
        PORTFILE.write_text(json.dumps({
            "port": PORT, "pid": os.getpid(), "started_at": time.time(),
            "db": str(VAULT_DB),
        }), encoding="utf-8")
    except OSError:
        pass


def _cleanup_portfile():
    try:
        # 우리 pid의 portfile만 제거(레이스로 다른 데몬이 덮어썼으면 보존)
        data = json.loads(PORTFILE.read_text(encoding="utf-8"))
        if data.get("pid") == os.getpid():
            PORTFILE.unlink()
    except (OSError, ValueError):
        pass


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
    _write_portfile()
    atexit.register(_cleanup_portfile)
    config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    # uvicorn 기본 시그널 핸들러 대신 우리 것 설치 → SIGTERM/SIGINT에 graceful 종료 + portfile 정리
    server.install_signal_handlers = lambda: None

    def _on_signal(_signum, _frame):
        server.should_exit = True
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    threading.Thread(target=_idle_watchdog, args=(server,), daemon=True).start()
    print(f"[daemon] llm-vault daemon up on http://127.0.0.1:{PORT} "
          f"(db={VAULT_DB}, idle_shutdown={IDLE_SHUTDOWN})", file=sys.stderr)
    try:
        server.run()
    finally:
        _cleanup_portfile()


if __name__ == "__main__":
    main()
