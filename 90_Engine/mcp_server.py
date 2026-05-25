#!/usr/bin/env python3
"""
90_Engine/mcp_server.py
Karpathy LLM Framework - MCP Server (stdio transport) v1.0

Cursor, Claude Desktop 등 MCP 클라이언트에 Vault LTM을 노출.

가동 (사용자가 직접 실행하지 않음; MCP 클라이언트가 spawn):
    python3 mcp_server.py

Cursor / Claude Desktop 설정 예시 (~/.cursor/mcp.json or claude_desktop_config.json):
{
  "mcpServers": {
    "karpathy-vault": {
      "command": "python3",
      "args": ["/absolute/path/to/90_Engine/mcp_server.py"],
      "env": {
        "VAULT_ROOT": "/absolute/path/to/vault",
        "VAULT_DB": "/absolute/path/to/90_Engine/ltm_cache.db",
        "OLLAMA_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "bge-m3"
      }
    }
  }
}

노출 도구:
  - retrieve_knowledge(query, top_k=5, max_hops=2): 자연어 쿼리 → 하이브리드 캡슐 컨텍스트
  - sync_vault(): indexer를 가동하여 신규/수정 노트를 DuckDB로 증분 컴파일
  - vault_stats(): 현재 그래프 통계 (노드/엣지/임베딩 커버리지/술어 분포)
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    sys.exit("ERROR: mcp 미설치. pip install mcp --break-system-packages")

# 같은 디렉터리의 retriever / indexer 모듈을 import
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

import retriever as retriever_mod
import indexer as indexer_mod


# ─────────────────────────────────────────────────────────────
# 환경 변수 (MCP 클라이언트의 config.env에서 주입)
# ─────────────────────────────────────────────────────────────
VAULT_ROOT = os.environ.get("VAULT_ROOT", str(SCRIPT_DIR.parent))
VAULT_DB = os.environ.get("VAULT_DB", str(SCRIPT_DIR / "ltm_cache.db"))
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "bge-m3")


# ─────────────────────────────────────────────────────────────
# Retriever 인스턴스 (lazy + cached)
# ─────────────────────────────────────────────────────────────
_retriever_cache: Optional["retriever_mod.Retriever"] = None

def get_retriever():
    global _retriever_cache
    if _retriever_cache is None:
        if not Path(VAULT_DB).exists():
            raise RuntimeError(
                f"DuckDB 캐시가 없습니다: {VAULT_DB}\n"
                f"먼저 'python3 indexer.py --embed --force' 실행 필요"
            )
        _retriever_cache = retriever_mod.Retriever(
            VAULT_DB, OLLAMA_URL, OLLAMA_MODEL
        )
    return _retriever_cache


def invalidate_retriever_cache():
    global _retriever_cache
    _retriever_cache = None


# ─────────────────────────────────────────────────────────────
# MCP 서버 정의
# ─────────────────────────────────────────────────────────────
mcp = FastMCP("karpathy-vault-ltm")


@mcp.tool()
def retrieve_knowledge(query: str, top_k: int = 5, max_hops: int = 2,
                        max_nodes: int = 10) -> dict:
    """Vault에서 자연어 쿼리에 가장 의미적으로 가까운 지식 서브그래프를 검색하여
    하이브리드 캡슐 포맷(JSON 메타 + XML 감싼 마크다운 본문)으로 반환합니다.

    Karpathy LLM Framework의 9개 술어 그래프 위에서 BM25 + Dense embedding의
    RRF 결합으로 seed nodes를 식별한 뒤, Adaptive 2-hop graph expansion으로
    의미 서브그래프를 확장합니다.

    Args:
        query: 자연어 질문 (한국어/영어 혼합 가능)
        top_k: 1차 검색에서 식별할 seed nodes 수 (기본 5)
        max_hops: 그래프 확장 최대 hop 수 (기본 2)
        max_nodes: 출력 XML 캡슐에 포함할 최대 노드 수 (기본 10)

    Returns:
        {
            "mode": "bm25+dense_sql" or "bm25" or "no_backend",
            "layer1_meta": {seed_nodes, activated_edges, node_scores, ...},
            "layer2_xml_capsule": "<retrieved_vault_context>...</retrieved_vault_context>"
        }
    """
    r = get_retriever()
    return r.retrieve(query, top_k=top_k, max_hops=max_hops, max_nodes=max_nodes)


@mcp.tool()
def sync_vault(force: bool = False, embed: bool = True) -> dict:
    """Vault 디렉터리를 스캔하여 신규/수정된 마크다운 노트를 DuckDB에 증분 컴파일.

    MD5 해시로 변경 감지하므로 무변경 파일은 건너뜁니다. embed=True이면 변경된
    노트만 Ollama로 재임베딩하여 nodes.embedding에 캐싱합니다.

    Args:
        force: True면 MD5 무관 모든 파일 강제 재인덱싱
        embed: True면 Ollama 임베딩 빌드 (Ollama 미가동 시 graceful skip)

    Returns:
        인덱싱 통계 (nodes_new, nodes_updated, edges_inserted, embeddings_built 등)
    """
    vault_root = Path(VAULT_ROOT).resolve()
    db_path = Path(VAULT_DB)
    stats, conn = indexer_mod.index_vault(
        vault_root, db_path,
        force_rebuild=force,
        embed=embed,
        ollama_url=OLLAMA_URL,
        embed_model=OLLAMA_MODEL,
    )
    conn.close()
    # 다음 검색에서 새 데이터 반영
    invalidate_retriever_cache()
    return stats


@mcp.tool()
def vault_stats() -> dict:
    """현재 Vault 그래프의 통계: 노드 수, 엣지 수, 임베딩 커버리지, 술어 분포,
    Hub Top 5, Authority Top 5를 반환.

    검색 호출 전 그래프 상태를 점검하거나, 변경 후 효과를 검증할 때 유용.

    Returns:
        {nodes_total, edges_total, embedding_coverage, predicate_distribution,
         hub_top5, authority_top5}
    """
    r = get_retriever()
    conn = r.conn
    pred_rows = conn.execute("""
        SELECT predicate, COUNT(*) AS cnt FROM edges
        GROUP BY predicate ORDER BY cnt DESC
    """).fetchall()
    hub_rows = conn.execute("""
        SELECT n.title, COUNT(e.edge_id) AS deg FROM nodes n
        LEFT JOIN edges e ON e.target_id = n.node_id
        GROUP BY n.title ORDER BY deg DESC, n.title LIMIT 5
    """).fetchall()
    auth_rows = conn.execute("""
        SELECT n.title, COUNT(e.edge_id) AS deg FROM nodes n
        LEFT JOIN edges e ON e.source_id = n.node_id
        GROUP BY n.title ORDER BY deg DESC, n.title LIMIT 5
    """).fetchall()
    n_emb = sum(1 for n in r.nodes.values() if n["has_embedding"])
    return {
        "nodes_total": len(r.nodes),
        "edges_total": len(r.edges),
        "embedding_coverage": f"{n_emb}/{len(r.nodes)}",
        "embedding_model": OLLAMA_MODEL,
        "predicate_distribution": {p: c for p, c in pred_rows},
        "hub_top5_in_degree": {t: d for t, d in hub_rows},
        "authority_top5_out_degree": {t: d for t, d in auth_rows},
    }


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # stdio transport (MCP 표준)
    mcp.run()
