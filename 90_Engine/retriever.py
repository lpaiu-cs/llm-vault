#!/usr/bin/env python3
"""
90_Engine/retriever.py
Karpathy LLM Framework - 2단 하이브리드 검색 런타임 v1.1

설계:
  1차: BM25(sparse) + Ollama Dense Embedding → RRF로 seed node 식별
       (임베딩은 indexer가 사전 컴파일, retriever는 DuckDB SQL cosine만 수행)
  2차: Adaptive 2-hop graph expansion (술어 가중치 + 노이즈 임계값)
  출력: 하이브리드 캡슐화 — JSON 메타/엣지(Layer 1) + XML 감싼 마크다운(Layer 2)

Triple Graceful Degradation:
  - Ollama 가동 + 임베딩 캐시 있음  → 풀 하이브리드
  - Ollama 미가동 또는 캐시 없음     → BM25-only fallback
  - DuckDB 없음                      → 명확한 에러
"""

import os
import re
import sys
import json
import uuid
import argparse
import json as _json
import urllib.request
import urllib.error
from pathlib import Path
from collections import defaultdict

try:
    import duckdb
except ImportError:
    sys.exit("ERROR: duckdb 미설치. pip install duckdb")

try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False

try:
    from fastapi import FastAPI
    from pydantic import BaseModel
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


# ─────────────────────────────────────────────────────────────
# §1. 상수
# ─────────────────────────────────────────────────────────────
PREDICATE_WEIGHTS = {
    "requires":       1.0,
    "implemented_by": 0.95,
    "causes":         0.9,
    "contradicts":    0.85,
    "abstracts":      0.8,
    "extends":        0.75,
    "replaces":       0.7,
    "utilizes":       0.6,
    "defines":        0.5,
}

ADAPTIVE_HOP_THRESHOLD = 0.3
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_EMBED_MODEL = "bge-m3"


# ─────────────────────────────────────────────────────────────
# §2. Ollama 쿼리 임베딩 (urllib만 사용)
# ─────────────────────────────────────────────────────────────
def ollama_embed(text, model=DEFAULT_EMBED_MODEL, base_url=DEFAULT_OLLAMA_URL, timeout=10):
    url = f"{base_url}/api/embed"
    payload = _json.dumps({"model": model, "input": text}).encode("utf-8")
    req = urllib.request.Request(url, data=payload,
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
        embeddings = data.get("embeddings") or data.get("embedding")
        if isinstance(embeddings, list) and embeddings:
            if isinstance(embeddings[0], list):
                return embeddings[0]
            return embeddings
        return None
    except Exception:
        return None


def normalize_vector(vec):
    if not vec:
        return vec
    norm = sum(x * x for x in vec) ** 0.5
    if norm == 0:
        return vec
    return [x / norm for x in vec]


# ─────────────────────────────────────────────────────────────
# §3. 데이터 로더
# ─────────────────────────────────────────────────────────────
def load_vault_graph(db_path):
    """DuckDB에서 노드/엣지 전체 로드 + 본문 텍스트 + 캐시된 임베딩."""
    conn = duckdb.connect(db_path, read_only=False)

    nodes = {}
    rows = conn.execute("""
        SELECT node_id, file_path, title, aliases, type, moc, md5_hash,
               embedding_model, embedding
        FROM nodes
    """).fetchall()
    for nid, fp, title, aliases, ntype, moc, md5, emb_model, embedding in rows:
        nid_str = str(nid)
        path = Path(fp)
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            content = ""
        nodes[nid_str] = {
            "node_id": nid_str,
            "title": title,
            "aliases": aliases or [],
            "type": ntype,
            "moc": moc,
            "md5_hash": md5,
            "file_path": str(path),
            "content": content,
            "embedding_model": emb_model,
            "has_embedding": embedding is not None,
        }

    edges = []
    rows = conn.execute("""
        SELECT source_id, target_id, predicate, evidence FROM edges
    """).fetchall()
    for src, tgt, pred, ev in rows:
        edges.append({
            "source_id": str(src),
            "target_id": str(tgt),
            "predicate": pred,
            "evidence": ev,
        })

    return conn, nodes, edges


# ─────────────────────────────────────────────────────────────
# §4. 1차 검색: BM25 + Dense (DuckDB SQL cosine)
# ─────────────────────────────────────────────────────────────
def tokenize_korean_english(text):
    text = text.lower()
    return re.findall(r"[가-힣]+|[a-z0-9]+", text)


def build_searchable_text(node):
    parts = [node["title"]]
    parts.extend(node.get("aliases", []))
    parts.append(node.get("content", ""))
    return " ".join(parts)


def reciprocal_rank_fusion(rankings, k=60):
    scores = defaultdict(float)
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] += 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: -x[1])


def dense_search_via_sql(conn, query_vec_normalized, top_k=20):
    """DuckDB array_cosine_similarity로 단일 SQL 쿼리.

    정규화된 벡터끼리는 cosine similarity == dot product.
    """
    # 임베딩이 있는 노드만 대상
    # list_cosine_similarity는 가변 크기 list/FLOAT[]를 받음 (array_cosine_similarity는 고정 크기만)
    rows = conn.execute("""
        SELECT node_id, list_cosine_similarity(embedding, ?::FLOAT[]) AS sim
        FROM nodes
        WHERE embedding IS NOT NULL
        ORDER BY sim DESC
        LIMIT ?
    """, [query_vec_normalized, top_k]).fetchall()
    return [(str(nid), float(sim)) for nid, sim in rows]


def hybrid_seed_search(query, conn, nodes, top_k=5,
                        ollama_url=DEFAULT_OLLAMA_URL,
                        embed_model=DEFAULT_EMBED_MODEL):
    """1차 검색: BM25 + Dense (캐시된 임베딩 + Ollama 쿼리 임베딩만 1회) → RRF."""
    node_ids = list(nodes.keys())
    rankings = []
    used_modes = []

    # BM25 sparse
    if HAS_BM25:
        corpus = [build_searchable_text(nodes[nid]) for nid in node_ids]
        tokenized = [tokenize_korean_english(d) for d in corpus]
        bm25 = BM25Okapi(tokenized)
        scores = bm25.get_scores(tokenize_korean_english(query))
        bm25_ranking = [node_ids[i] for i in sorted(range(len(scores)),
                                                      key=lambda i: -scores[i])]
        rankings.append(bm25_ranking)
        used_modes.append("bm25")

    # Dense (Ollama 쿼리 임베딩 1회 + DuckDB SQL)
    has_any_cached = any(n["has_embedding"] for n in nodes.values())
    if has_any_cached:
        query_vec = ollama_embed(query, model=embed_model, base_url=ollama_url)
        if query_vec is not None:
            query_norm = normalize_vector(query_vec)
            sql_results = dense_search_via_sql(conn, query_norm, top_k=max(top_k * 4, 20))
            dense_ranking = [nid for nid, _ in sql_results]
            # 캐시 없는 노드들을 뒤에 append (BM25 fallback 보장)
            for nid in node_ids:
                if nid not in dense_ranking:
                    dense_ranking.append(nid)
            rankings.append(dense_ranking)
            used_modes.append("dense_sql")

    if not rankings:
        return [], "no_backend"

    fused = reciprocal_rank_fusion(rankings)
    seed_ids = [doc_id for doc_id, _ in fused[:top_k]]
    return seed_ids, "+".join(used_modes)


# ─────────────────────────────────────────────────────────────
# §5. 2차 검색: Adaptive Graph Expansion
# ─────────────────────────────────────────────────────────────
def adaptive_hop_expansion(seed_ids, edges, max_hops=2, threshold=ADAPTIVE_HOP_THRESHOLD):
    adj = defaultdict(list)
    for e in edges:
        adj[e["source_id"]].append((e["target_id"], e["predicate"], "out"))
        adj[e["target_id"]].append((e["source_id"], e["predicate"], "in"))

    node_scores = defaultdict(float)
    activated_edges = []
    visited = set(seed_ids)
    for sid in seed_ids:
        node_scores[sid] = 1.0

    frontier_1hop = set()
    for sid in seed_ids:
        for neighbor, predicate, direction in adj[sid]:
            weight = PREDICATE_WEIGHTS.get(predicate, 0.5)
            edge_score = node_scores[sid] * weight
            node_scores[neighbor] = max(node_scores[neighbor], edge_score)
            frontier_1hop.add(neighbor)
            activated_edges.append({
                "source_id": sid if direction == "out" else neighbor,
                "target_id": neighbor if direction == "out" else sid,
                "predicate": predicate,
                "hop": 1,
                "score": edge_score,
            })
            visited.add(neighbor)

    if max_hops >= 2:
        candidates = [n for n in frontier_1hop if node_scores[n] >= threshold]
        for mid in candidates:
            for neighbor, predicate, direction in adj[mid]:
                if neighbor in visited:
                    continue
                weight = PREDICATE_WEIGHTS.get(predicate, 0.5)
                edge_score = node_scores[mid] * weight * 0.7
                node_scores[neighbor] = max(node_scores[neighbor], edge_score)
                activated_edges.append({
                    "source_id": mid if direction == "out" else neighbor,
                    "target_id": neighbor if direction == "out" else mid,
                    "predicate": predicate,
                    "hop": 2,
                    "score": edge_score,
                })
                visited.add(neighbor)

    ranked = sorted(node_scores.items(), key=lambda x: -x[1])
    return [nid for nid, _ in ranked], node_scores, activated_edges


# ─────────────────────────────────────────────────────────────
# §6. 하이브리드 캡슐화 출력
# ─────────────────────────────────────────────────────────────
def strip_frontmatter(content):
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            return content[end + 4:].lstrip()
    return content


def format_hybrid_output(query, seed_ids, ranked_ids, node_scores,
                          activated_edges, nodes, max_nodes=10):
    layer1 = {
        "query": query,
        "seed_nodes": [nodes[sid]["title"] for sid in seed_ids if sid in nodes],
        "retrieved_nodes_count": len(ranked_ids),
        "activated_edges": [
            f"[[{nodes[e['source_id']]['title']}]] {e['predicate']} [[{nodes[e['target_id']]['title']}]]"
            for e in activated_edges
            if e["source_id"] in nodes and e["target_id"] in nodes
        ][:20],
        "node_scores": {
            nodes[nid]["title"]: round(node_scores[nid], 4)
            for nid in ranked_ids[:max_nodes]
            if nid in nodes
        },
    }
    xml_parts = ["<retrieved_vault_context>"]
    for nid in ranked_ids[:max_nodes]:
        if nid not in nodes:
            continue
        n = nodes[nid]
        body = strip_frontmatter(n["content"])
        xml_parts.append(
            f'  <node id="{nid}" title="{n["title"]}" type="{n["type"] or ""}">\n'
            f'{body}\n'
            f'  </node>'
        )
    xml_parts.append("</retrieved_vault_context>")
    return {
        "layer1_meta": layer1,
        "layer2_xml_capsule": "\n".join(xml_parts),
    }


# ─────────────────────────────────────────────────────────────
# §7. Retriever 클래스
# ─────────────────────────────────────────────────────────────
class Retriever:
    def __init__(self, db_path, ollama_url=DEFAULT_OLLAMA_URL,
                 embed_model=DEFAULT_EMBED_MODEL):
        self.db_path = db_path
        self.ollama_url = ollama_url
        self.embed_model = embed_model
        self.conn, self.nodes, self.edges = load_vault_graph(db_path)
        n_with_emb = sum(1 for n in self.nodes.values() if n["has_embedding"])
        print(f"[*] Loaded {len(self.nodes)} nodes, {len(self.edges)} edges "
              f"({n_with_emb} with embedding)")

    def retrieve(self, query, top_k=5, max_hops=2,
                 threshold=ADAPTIVE_HOP_THRESHOLD, max_nodes=10):
        seed_ids, mode = hybrid_seed_search(
            query, self.conn, self.nodes, top_k=top_k,
            ollama_url=self.ollama_url, embed_model=self.embed_model
        )
        ranked_ids, node_scores, activated = adaptive_hop_expansion(
            seed_ids, self.edges, max_hops=max_hops, threshold=threshold
        )
        output = format_hybrid_output(
            query, seed_ids, ranked_ids, node_scores, activated,
            self.nodes, max_nodes=max_nodes
        )
        output["mode"] = mode
        return output


# ─────────────────────────────────────────────────────────────
# §8. FastAPI
# ─────────────────────────────────────────────────────────────
if HAS_FASTAPI:
    class RetrieveRequest(BaseModel):
        query: str
        top_k: int = 5
        max_hops: int = 2
        threshold: float = ADAPTIVE_HOP_THRESHOLD
        max_nodes: int = 10

    app = FastAPI(title="Karpathy LLM Framework Retriever v1.1")
    _instance = None

    def get_retriever():
        global _instance
        if _instance is None:
            db = os.environ.get("VAULT_DB", "/tmp/ltm_v5.db")
            url = os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL)
            model = os.environ.get("OLLAMA_MODEL", DEFAULT_EMBED_MODEL)
            _instance = Retriever(db, url, model)
        return _instance

    @app.post("/retrieve")
    def retrieve_endpoint(req: RetrieveRequest):
        return get_retriever().retrieve(
            req.query, top_k=req.top_k, max_hops=req.max_hops,
            threshold=req.threshold, max_nodes=req.max_nodes
        )

    @app.get("/health")
    def health():
        r = get_retriever()
        n_emb = sum(1 for n in r.nodes.values() if n["has_embedding"])
        return {
            "status": "ok",
            "node_count": len(r.nodes),
            "edge_count": len(r.edges),
            "embedding_coverage": f"{n_emb}/{len(r.nodes)}",
        }


def main():
    parser = argparse.ArgumentParser(description="Karpathy LLM Framework Retriever v1.1")
    parser.add_argument("--query", required=True)
    parser.add_argument("--db", default="/tmp/ltm_v5.db")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--hops", type=int, default=2)
    parser.add_argument("--threshold", type=float, default=ADAPTIVE_HOP_THRESHOLD)
    parser.add_argument("--max-nodes", type=int, default=10)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--ollama-model", default=DEFAULT_EMBED_MODEL)
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    r = Retriever(args.db, args.ollama_url, args.ollama_model)
    result = r.retrieve(args.query, top_k=args.top_k, max_hops=args.hops,
                         threshold=args.threshold, max_nodes=args.max_nodes)
    print()
    print("=" * 64)
    print(f"  Query: {args.query}")
    print(f"  Mode: {result['mode']}")
    print("=" * 64)
    print()
    print("── Layer 1 (JSON) ──")
    print(_json.dumps(result["layer1_meta"], ensure_ascii=False, indent=2))
    if not args.json_only:
        print()
        print("── Layer 2 (XML) ──")
        print(result["layer2_xml_capsule"][:2500])
        if len(result["layer2_xml_capsule"]) > 2500:
            print(f"... ({len(result['layer2_xml_capsule']) - 2500}자 더)")


if __name__ == "__main__":
    main()
