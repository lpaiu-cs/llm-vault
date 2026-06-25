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
import time
import argparse
import json as _json
import urllib.request
import urllib.error
from pathlib import Path
from contextlib import closing
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
# §1.5 Second Brain 계층/신뢰도 인지 검색 (layer & confidence aware)
# ─────────────────────────────────────────────────────────────
# 랭킹 가중치·필터·주석은 설정 파일(00_System/Retrieval Policy.yaml 또는
# 90_Engine/retrieval_policy.yaml, 또는 env VAULT_RETRIEVAL_POLICY)에서 로드한다.
# 아래 상수는 "설정이 없을 때의 fallback default"다. 이 값들은 경험적 최적값이
# 아니라 **잠정적 사전값(provisional prior)**이며, 실측 튜닝은 eval_retrieval.py로 한다.

# ── Fallback: 계층 랭킹 가중치 (검증 지식↑, 원본/검토 계층↓) ──
LAYER_RANK_WEIGHT = {
    "20_Concepts": 1.0, "50_Source_Summaries": 1.0, "10_MOC": 0.95,
    "40_Decisions": 0.95, "30_Projects": 0.9, "00_System": 0.85,
    "06_Raw": 0.5, "60_Open_Questions": 0.45, "70_Contradictions": 0.45,
    "80_Reviews": 0.35,
}
DEFAULT_LAYER_WEIGHT = 0.8

# ── Fallback: 기본 검색 포함 여부(필터) — 가중치와 분리. 미지정은 default_include ──
LAYER_DEFAULT_INCLUDE = {
    "60_Open_Questions": False, "70_Contradictions": False, "80_Reviews": False,
}
DEFAULT_LAYER_INCLUDE = True

# ── Fallback: 결과 주석(annotation) ──
LAYER_ANNOTATION = {
    "06_Raw": "raw evidence, unprocessed",
    "50_Source_Summaries": "source summary",
    "40_Decisions": "decision record",
    "30_Projects": "project dashboard",
    "20_Concepts": "durable concept",
    "10_MOC": "map of content",
    "00_System": "system policy",
    "60_Open_Questions": "open question",
    "70_Contradictions": "contradiction / unresolved",
    "80_Reviews": "low-confidence / possible hallucination",
}
DEFAULT_ANNOTATION = ""

# ── Fallback: 신뢰도/상태 가중치 ──
CONFIDENCE_WEIGHT = {"high": 1.0, "medium": 0.85, "low": 0.6}
DEFAULT_CONFIDENCE_WEIGHT = 1.0
STATUS_WEIGHT = {"active": 1.0, "evergreen": 1.0, "open": 1.0,
                 "superseded": 0.3, "rejected": 0.25, "deprecated": 0.3, "stale": 0.4}
DEFAULT_STATUS_WEIGHT = 1.0

# 원본/검토 계층 식별 (필터 toggle용 상수)
REVIEW_LAYERS = ("60_Open_Questions", "70_Contradictions", "80_Reviews")
RAW_LAYER = "06_Raw"

# 설정 파일 이름
POLICY_FILENAME_SYSTEM = "Retrieval Policy.yaml"   # 00_System/
POLICY_FILENAME_ENGINE = "retrieval_policy.yaml"   # 90_Engine/

try:
    import yaml as _yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

_LAYER_DIR_RE = re.compile(r"^\d{2}_")


def layer_from_path(file_path):
    """파일 경로에서 최상위 계층 폴더('NN_Name')를 추출. 없으면 None(루트 문서 등)."""
    for part in Path(file_path).parts:
        if _LAYER_DIR_RE.match(part):
            return part
    return None


def parse_frontmatter_fields(content):
    """frontmatter에서 스칼라 필드만 가볍게 추출(confidence/status 등). 없으면 {}."""
    if not content.startswith("---"):
        return {}
    end = content.find("\n---", 3)
    if end == -1:
        return {}
    out = {}
    for line in content[3:end].splitlines():
        s = line.strip()
        if ":" in s and not s.startswith("-") and not s.startswith("#"):
            k, _, v = s.partition(":")
            out[k.strip().lower()] = v.strip().strip('"').strip("'")
    return out


# ─────────────────────────────────────────────────────────────
# §1.6 Retrieval Policy 로더 (PyYAML 있으면 사용, 없으면 내장 최소 파서)
# ─────────────────────────────────────────────────────────────
def _coerce_scalar(v):
    v = v.strip()
    if (v[:1] == '"' and v[-1:] == '"') or (v[:1] == "'" and v[-1:] == "'"):
        return v[1:-1]
    low = v.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "~", ""):
        return None
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    try:
        return float(v)
    except ValueError:
        return v


def _parse_block_yaml(text):
    """의존성 없는 최소 블록 YAML 파서(중첩 맵 + 스칼라). 리스트/인라인 flow 미지원.
    PyYAML 미설치 시의 fallback 경로. 들여쓰기는 공백 기준."""
    root = {}
    stack = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if ":" not in line:
            continue  # 리스트 항목 등은 미지원 → 스킵
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        key, _, val = line.partition(":")
        key = key.strip().strip('"').strip("'")
        val = val.strip()
        if val == "":
            child = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _coerce_scalar(val)
    return root


def _load_policy_file(path):
    text = Path(path).read_text(encoding="utf-8")
    if HAS_YAML:
        return _yaml.safe_load(text) or {}
    return _parse_block_yaml(text)


def _resolve_policy(cfg):
    """파일 설정(cfg)을 fallback default 위에 병합해 해석된 정책 dict를 반환."""
    cfg = cfg if isinstance(cfg, dict) else {}
    layers_cfg = cfg.get("layers") or {}
    lw, li, la = dict(LAYER_RANK_WEIGHT), dict(LAYER_DEFAULT_INCLUDE), dict(LAYER_ANNOTATION)
    for name, spec in layers_cfg.items():
        spec = spec or {}
        if spec.get("weight") is not None:
            lw[name] = float(spec["weight"])
        if spec.get("default_include") is not None:
            li[name] = bool(spec["default_include"])
        if spec.get("annotation") is not None:
            la[name] = str(spec["annotation"])
    dl = cfg.get("default_layer") or {}
    cw = dict(CONFIDENCE_WEIGHT)
    cw.update({k: float(v) for k, v in (cfg.get("confidence_weight") or {}).items()})
    sw = dict(STATUS_WEIGHT)
    sw.update({k: float(v) for k, v in (cfg.get("status_weight") or {}).items()})
    # 파일 단위 override (layer보다 우선; 키는 vault 루트 기준 상대 경로)
    files_cfg = cfg.get("files") or {}
    fw, fi, fa = {}, {}, {}
    for name, spec in files_cfg.items():
        spec = spec or {}
        if spec.get("weight") is not None:
            fw[name] = float(spec["weight"])
        if spec.get("default_include") is not None:
            fi[name] = bool(spec["default_include"])
        if spec.get("annotation") is not None:
            fa[name] = str(spec["annotation"])
    return {
        "layer_weight": lw,
        "default_layer_weight": float(dl.get("weight", DEFAULT_LAYER_WEIGHT)),
        "layer_include": li,
        "default_include": bool(dl.get("default_include", DEFAULT_LAYER_INCLUDE)),
        "layer_annotation": la,
        "default_annotation": str(dl.get("annotation", DEFAULT_ANNOTATION)),
        "file_weight": fw,
        "file_include": fi,
        "file_annotation": fa,
        "confidence_weight": cw,
        "default_confidence_weight": float(cfg.get("default_confidence_weight", DEFAULT_CONFIDENCE_WEIGHT)),
        "status_weight": sw,
        "default_status_weight": float(cfg.get("default_status_weight", DEFAULT_STATUS_WEIGHT)),
        "raw_policy": cfg.get("raw_policy") or {"embed": True},
    }


def load_retrieval_policy(vault_root=None, explicit_path=None):
    """설정 파일을 찾아 해석된 정책을 반환. 없으면 fallback default.

    Returns: (policy_dict, source_path_or_None)
    """
    candidates = []
    if explicit_path:
        candidates.append(Path(explicit_path))
    env = os.environ.get("VAULT_RETRIEVAL_POLICY")
    if env:
        candidates.append(Path(env))
    if vault_root:
        candidates.append(Path(vault_root) / "00_System" / POLICY_FILENAME_SYSTEM)
    candidates.append(Path(__file__).resolve().parent / POLICY_FILENAME_ENGINE)
    for c in candidates:
        try:
            if c and c.exists():
                return _resolve_policy(_load_policy_file(c)), str(c)
        except Exception as e:
            sys.stderr.write(f"[retriever] 정책 파일 로드 실패({c}): {e} — fallback 사용\n")
            continue
    return _resolve_policy({}), None


# 설정 파일 없을 때의 해석된 fallback 정책
DEFAULT_RETRIEVAL_POLICY = _resolve_policy({})


def compute_rank_weight(layer, confidence, status, confidence_weighting=True, policy=None):
    """계층 × 신뢰도 × 상태 가중치 곱. policy 미지정 시 fallback default 사용."""
    pol = policy or DEFAULT_RETRIEVAL_POLICY
    w = pol["layer_weight"].get(layer, pol["default_layer_weight"])
    if confidence_weighting and confidence:
        w *= pol["confidence_weight"].get(str(confidence).lower(),
                                          pol["default_confidence_weight"])
    if status:
        w *= pol["status_weight"].get(str(status).lower(), pol["default_status_weight"])
    return w


def layer_included(layer, policy=None):
    """기본 검색 스코프 포함 여부(필터, 계층 기준). policy 미지정 시 fallback."""
    pol = policy or DEFAULT_RETRIEVAL_POLICY
    return pol["layer_include"].get(layer, pol["default_include"])


# ── 노드 단위 해석: 파일 override(rel_path) > 계층(layer) ──
def _node_base_weight(node, pol):
    rel = node.get("rel_path")
    if rel and rel in pol.get("file_weight", {}):
        return pol["file_weight"][rel]
    return pol["layer_weight"].get(node.get("layer"), pol["default_layer_weight"])


def node_rank_weight(node, policy=None, confidence_weighting=True):
    """노드의 최종 랭킹 가중치 = (파일 또는 계층 기본가중치) × confidence × status."""
    pol = policy or DEFAULT_RETRIEVAL_POLICY
    w = _node_base_weight(node, pol)
    conf, status = node.get("confidence"), node.get("status")
    if confidence_weighting and conf:
        w *= pol["confidence_weight"].get(str(conf).lower(), pol["default_confidence_weight"])
    if status:
        w *= pol["status_weight"].get(str(status).lower(), pol["default_status_weight"])
    return w


def node_included(node, policy=None):
    """노드의 기본 검색 포함 여부. 파일 override > 계층."""
    pol = policy or DEFAULT_RETRIEVAL_POLICY
    rel = node.get("rel_path")
    if rel and rel in pol.get("file_include", {}):
        return pol["file_include"][rel]
    return pol["layer_include"].get(node.get("layer"), pol["default_include"])


def node_annotation(node, policy=None):
    """노드 주석. 파일 override > 계층."""
    pol = policy or DEFAULT_RETRIEVAL_POLICY
    rel = node.get("rel_path")
    if rel and rel in pol.get("file_annotation", {}):
        return pol["file_annotation"][rel]
    return pol["layer_annotation"].get(node.get("layer"), pol["default_annotation"])


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
def connect_db(db_path, read_only=True, retries=20, delay=0.25):
    """DuckDB 연결을 '짧게 잡고 바로 닫는' 용도로 연다. 락 충돌 시 잠깐 재시도.

    여러 MCP 클라이언트(Claude/Codex/Antigravity)가 같은 ltm_cache.db에 동시에
    붙는 환경에서, read-write 연결을 프로세스 수명 내내 들고 있으면 DuckDB의
    single-writer 락 때문에 다른 클라이언트가 'Conflicting lock'으로 막힌다.
    그래서 reader는 read_only=True(공유 락, 다중 프로세스 동시 가능)로, writer는
    단명 read_only=False로만 열고 즉시 닫는다.
    """
    last = None
    for _ in range(retries):
        try:
            return duckdb.connect(db_path, read_only=read_only)
        except Exception as e:  # duckdb.IOException 등: 락 충돌이면 잠깐 대기 후 재시도
            if "lock" not in str(e).lower():
                raise
            last = e
            time.sleep(delay)
    raise last


def load_vault_graph(db_path, vault_root=None):
    """DuckDB에서 노드/엣지 전체 로드 + 본문 텍스트 + 캐시된 임베딩.
    vault_root를 주면 노드에 rel_path(파일 단위 정책용)를 함께 채운다.

    그래프는 메모리에 적재한 뒤 연결을 즉시 닫는다(영속 락 보유 금지)."""
    conn = connect_db(db_path, read_only=True)
    vr = Path(vault_root).resolve() if vault_root else None

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
        fm = parse_frontmatter_fields(content)
        rel = None
        if vr:
            try:
                rel = path.resolve().relative_to(vr).as_posix()
            except (ValueError, OSError):
                rel = None
        nodes[nid_str] = {
            "node_id": nid_str,
            "title": title,
            "aliases": aliases or [],
            "type": ntype,
            "moc": moc,
            "md5_hash": md5,
            "file_path": str(path),
            "rel_path": rel,
            "content": content,
            "embedding_model": emb_model,
            "has_embedding": embedding is not None,
            # Second Brain 계층/신뢰도 메타 (경로·frontmatter에서 파생)
            "layer": layer_from_path(fp),
            "confidence": fm.get("confidence"),
            "status": fm.get("status"),
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

    conn.close()
    return nodes, edges


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
                        embed_model=DEFAULT_EMBED_MODEL,
                        allowed_ids=None, weights=None):
    """1차 검색: BM25 + Dense (캐시된 임베딩 + Ollama 쿼리 임베딩만 1회) → RRF.

    allowed_ids: 검색 후보를 이 집합으로 제한(계층 스코프 필터). None이면 전체.
    weights:     {node_id: 가중치}. RRF 융합 점수에 곱해 계층/신뢰도를 반영.
    """
    if allowed_ids is None:
        node_ids = list(nodes.keys())
    else:
        node_ids = [nid for nid in nodes.keys() if nid in allowed_ids]
    if not node_ids:
        return [], "no_candidates"
    weights = weights or {}
    allowed_set = set(node_ids)
    rankings = []
    used_modes = []

    # BM25 sparse (후보 집합만 코퍼스로)
    if HAS_BM25:
        corpus = [build_searchable_text(nodes[nid]) for nid in node_ids]
        tokenized = [tokenize_korean_english(d) for d in corpus]
        bm25 = BM25Okapi(tokenized)
        scores = bm25.get_scores(tokenize_korean_english(query))
        bm25_ranking = [node_ids[i] for i in sorted(range(len(scores)),
                                                      key=lambda i: -scores[i])]
        rankings.append(bm25_ranking)
        used_modes.append("bm25")

    # Dense (Ollama 쿼리 임베딩 1회 + DuckDB SQL → 후보 집합으로 필터)
    has_any_cached = any(nodes[nid]["has_embedding"] for nid in node_ids)
    if has_any_cached:
        query_vec = ollama_embed(query, model=embed_model, base_url=ollama_url)
        if query_vec is not None:
            query_norm = normalize_vector(query_vec)
            sql_results = dense_search_via_sql(conn, query_norm, top_k=max(top_k * 8, 40))
            dense_ranking = [nid for nid, _ in sql_results if nid in allowed_set]
            # 캐시 없는 후보들을 뒤에 append (BM25 fallback 보장)
            for nid in node_ids:
                if nid not in dense_ranking:
                    dense_ranking.append(nid)
            rankings.append(dense_ranking)
            used_modes.append("dense_sql")

    if not rankings:
        return [], "no_backend"

    fused = reciprocal_rank_fusion(rankings)
    # 계층/신뢰도 가중치 적용 후 재정렬
    weighted = sorted(
        ((doc_id, score * weights.get(doc_id, 1.0)) for doc_id, score in fused),
        key=lambda x: -x[1],
    )
    seed_ids = [doc_id for doc_id, _ in weighted[:top_k]]
    return seed_ids, "+".join(used_modes)


# ─────────────────────────────────────────────────────────────
# §5. 2차 검색: Adaptive Graph Expansion
# ─────────────────────────────────────────────────────────────
def adaptive_hop_expansion(seed_ids, edges, max_hops=2, threshold=ADAPTIVE_HOP_THRESHOLD,
                           weights=None):
    """weights: {node_id: 계층/신뢰도 가중치}. 각 노드 점수에 곱해 강등을 전파."""
    weights = weights or {}

    def nw(nid):
        return weights.get(nid, 1.0)

    adj = defaultdict(list)
    for e in edges:
        adj[e["source_id"]].append((e["target_id"], e["predicate"], "out"))
        adj[e["target_id"]].append((e["source_id"], e["predicate"], "in"))

    node_scores = defaultdict(float)
    activated_edges = []
    visited = set(seed_ids)
    for sid in seed_ids:
        node_scores[sid] = 1.0 * nw(sid)

    frontier_1hop = set()
    for sid in seed_ids:
        for neighbor, predicate, direction in adj[sid]:
            weight = PREDICATE_WEIGHTS.get(predicate, 0.5)
            edge_score = node_scores[sid] * weight * nw(neighbor)
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
                edge_score = node_scores[mid] * weight * 0.7 * nw(neighbor)
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
                          activated_edges, nodes, max_nodes=10, annotations=None):
    out_ids = [nid for nid in ranked_ids[:max_nodes] if nid in nodes]
    annotations = annotations or {}
    layer1 = {
        "query": query,
        "seed_nodes": [nodes[sid]["title"] for sid in seed_ids if sid in nodes],
        "retrieved_nodes_count": len(ranked_ids),
        "activated_edges": [
            f"[[{nodes[e['source_id']]['title']}]] {e['predicate']} [[{nodes[e['target_id']]['title']}]]"
            for e in activated_edges
            if e["source_id"] in nodes and e["target_id"] in nodes
        ][:20],
        # 계층/신뢰도/상태/주석을 함께 표기 → 에이전트가 출처·불확실성을 스스로 판단
        "nodes": [
            {
                "title": nodes[nid]["title"],
                "layer": nodes[nid].get("layer"),
                "type": nodes[nid].get("type"),
                "confidence": nodes[nid].get("confidence"),
                "status": nodes[nid].get("status"),
                "annotation": annotations.get(nid),
                "score": round(node_scores[nid], 4),
            }
            for nid in out_ids
        ],
        "node_scores": {  # 하위 호환: title → score
            nodes[nid]["title"]: round(node_scores[nid], 4) for nid in out_ids
        },
    }
    xml_parts = ["<retrieved_vault_context>"]
    for nid in out_ids:
        n = nodes[nid]
        body = strip_frontmatter(n["content"])
        attrs = (f'id="{nid}" title="{n["title"]}" type="{n["type"] or ""}" '
                 f'layer="{n.get("layer") or ""}"')
        if n.get("confidence"):
            attrs += f' confidence="{n["confidence"]}"'
        if n.get("status"):
            attrs += f' status="{n["status"]}"'
        if annotations.get(nid):
            attrs += f' annotation="{annotations[nid]}"'
        xml_parts.append(f'  <node {attrs}>\n{body}\n  </node>')
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
                 embed_model=DEFAULT_EMBED_MODEL, vault_root=None,
                 policy_path=None):
        self.db_path = db_path
        self.ollama_url = ollama_url
        self.embed_model = embed_model
        # vault_root: 명시값 → 없으면 db 경로(90_Engine/ltm_cache.db)에서 추정
        self.vault_root = (Path(vault_root).resolve() if vault_root
                           else Path(db_path).resolve().parent.parent)
        self.policy, self.policy_source = load_retrieval_policy(
            self.vault_root, explicit_path=policy_path)
        self.nodes, self.edges = load_vault_graph(db_path, self.vault_root)
        n_with_emb = sum(1 for n in self.nodes.values() if n["has_embedding"])
        print(f"[*] Loaded {len(self.nodes)} nodes, {len(self.edges)} edges "
              f"({n_with_emb} with embedding)", file=sys.stderr)
        print(f"[*] Retrieval policy: {self.policy_source or 'built-in fallback (provisional prior)'}", file=sys.stderr)

    def retrieve(self, query, top_k=5, max_hops=2,
                 threshold=ADAPTIVE_HOP_THRESHOLD, max_nodes=10,
                 include_raw=True, include_reviews=False,
                 include_layers=None, exclude_layers=None,
                 confidence_weighting=True):
        """계층/신뢰도 인지 검색. 가중치·필터·주석은 Retrieval Policy(설정)에서 온다.

        include_raw:      06_Raw(full-text 전용)를 후보에 포함할지 (기본 True, 강등됨)
        include_reviews:  기본 제외(default_include=false) 계층까지 포함할지 (기본 False)
        include_layers:   주면 이 계층들로만 제한(다른 필터 무시)
        exclude_layers:   추가로 제외할 계층 목록
        confidence_weighting: confidence(low/medium) 강등 적용 여부 (기본 True)
        """
        pol = self.policy

        # ── 검색 스코프: 노드 단위 필터(파일 override > 계층 default_include) ──
        if include_layers is not None:
            sel = set(include_layers)
            allowed_ids = {nid for nid, n in self.nodes.items()
                           if n.get("layer") in sel}
        else:
            allowed_ids = set()
            for nid, n in self.nodes.items():
                inc = node_included(n, pol)
                if include_reviews and not inc:  # 기본 제외 계층/파일까지 포함
                    inc = True
                if inc:
                    allowed_ids.add(nid)
            if not include_raw:
                allowed_ids -= {nid for nid in allowed_ids
                                if self.nodes[nid].get("layer") == RAW_LAYER}
            if exclude_layers:
                ex = set(exclude_layers)
                allowed_ids -= {nid for nid in allowed_ids
                                if self.nodes[nid].get("layer") in ex}

        # ── 랭킹 가중치·주석: 노드 단위(파일 override > 계층) ──
        weights = {
            nid: node_rank_weight(n, pol, confidence_weighting)
            for nid, n in self.nodes.items()
        }
        annotations = {
            nid: node_annotation(n, pol) for nid, n in self.nodes.items()
        }

        with closing(connect_db(self.db_path, read_only=True)) as conn:
            seed_ids, mode = hybrid_seed_search(
                query, conn, self.nodes, top_k=top_k,
                ollama_url=self.ollama_url, embed_model=self.embed_model,
                allowed_ids=allowed_ids, weights=weights,
            )
        ranked_ids, node_scores, activated = adaptive_hop_expansion(
            seed_ids, self.edges, max_hops=max_hops, threshold=threshold,
            weights=weights,
        )
        # 출력 스코프 필터: 제외 계층은 그래프 확장으로 끌려와도 결과에서 뺀다
        ranked_ids = [nid for nid in ranked_ids if nid in allowed_ids]
        output = format_hybrid_output(
            query, seed_ids, ranked_ids, node_scores, activated,
            self.nodes, max_nodes=max_nodes, annotations=annotations,
        )
        output["mode"] = mode
        output["scope"] = {
            "include_raw": include_raw,
            "include_reviews": include_reviews,
            "allowed_layers": sorted({self.nodes[nid].get("layer")
                                      for nid in allowed_ids
                                      if self.nodes[nid].get("layer")}),
            "policy_source": self.policy_source or "built-in fallback",
        }
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
        include_raw: bool = True
        include_reviews: bool = False
        confidence_weighting: bool = True

    app = FastAPI(title="Karpathy LLM Framework Retriever v1.1")
    _instance = None

    def get_retriever():
        global _instance
        if _instance is None:
            db = os.environ.get("VAULT_DB", "/tmp/ltm_v5.db")
            url = os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL)
            model = os.environ.get("OLLAMA_MODEL", DEFAULT_EMBED_MODEL)
            _instance = Retriever(db, url, model,
                                  vault_root=os.environ.get("VAULT_ROOT"))
        return _instance

    @app.post("/retrieve")
    def retrieve_endpoint(req: RetrieveRequest):
        return get_retriever().retrieve(
            req.query, top_k=req.top_k, max_hops=req.max_hops,
            threshold=req.threshold, max_nodes=req.max_nodes,
            include_raw=req.include_raw, include_reviews=req.include_reviews,
            confidence_weighting=req.confidence_weighting,
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
    parser.add_argument("--policy", default=None, help="Retrieval Policy 파일 경로(override)")
    parser.add_argument("--vault-root", default=None, help="vault 루트(정책 탐색용)")
    parser.add_argument("--include-reviews", action="store_true",
                        help="60/70/80 검토·메타 계층까지 검색에 포함")
    parser.add_argument("--no-raw", action="store_true", help="06_Raw 제외")
    parser.add_argument("--no-confidence-weighting", action="store_true",
                        help="confidence 강등 끄기")
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    r = Retriever(args.db, args.ollama_url, args.ollama_model,
                  vault_root=args.vault_root, policy_path=args.policy)
    result = r.retrieve(args.query, top_k=args.top_k, max_hops=args.hops,
                         threshold=args.threshold, max_nodes=args.max_nodes,
                         include_raw=not args.no_raw,
                         include_reviews=args.include_reviews,
                         confidence_weighting=not args.no_confidence_weighting)
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
