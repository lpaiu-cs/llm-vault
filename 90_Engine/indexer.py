#!/usr/bin/env python3
"""
90_Engine/indexer.py
Karpathy LLM Framework - Vault Indexer v1.1

마크다운 Vault를 DuckDB 그래프 캐시로 컴파일 + Ollama 임베딩 캐싱.
Ontology Specification v1.0을 강제합니다.

사용:
    # 기본 (엣지만 인덱싱, 임베딩 없음)
    python3 indexer.py --report

    # 임베딩까지 풀 컴파일 (Ollama 가동 중일 때)
    python3 indexer.py --embed --report

    # 강제 재인덱싱 + 재임베딩
    python3 indexer.py --force --embed --report
"""

import os
import re
import sys
import json
import hashlib
import uuid
import argparse
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

try:
    import duckdb
except ImportError:
    sys.exit("ERROR: duckdb 미설치. pip install duckdb --break-system-packages")


# ─────────────────────────────────────────────────────────────
# §1. 헌법 상수
# ─────────────────────────────────────────────────────────────
ALLOWED_PREDICATES = (
    "abstracts", "causes", "contradicts", "defines", "extends",
    "implemented_by", "replaces", "requires", "utilizes",
)

EDGE_REGEX = re.compile(
    r"^-\s+"
    r"`\[\[(?P<source>.+?)\]\]"
    r"\s+(?P<predicate>\w+)\s+"
    r"\[\[(?P<target>.+?)\]\]`"
    r"(?:\s*—\s*(?P<desc>.*))?$"
)

FRONTMATTER_REGEX = re.compile(
    r"\A---\s*\n(?P<meta>.*?)\n---\s*\n",
    re.DOTALL
)

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_EMBED_MODEL = "bge-m3"


# ─────────────────────────────────────────────────────────────
# §1.5 Second Brain 계층별 인덱싱 정책 (per-folder index policy)
# ─────────────────────────────────────────────────────────────
# 디렉터리 이름 기반 단순 제외를 넘어, 계층(layer)별로 인덱싱 동작을 분리한다.
# 각 정책 키:
#   index       : DuckDB nodes 테이블에 node로 적재할지
#   embed       : Ollama 임베딩(dense 검색 대상)을 만들지
#   parse_edges : 본문에서 9술어 edge-DSL을 파싱할지
#   graph_node  : wikilink/edge 타깃(=링크 네임스페이스, title_to_id)에 넣을지
#   role        : 분류 라벨 (retriever가 가중치/스코프에 활용; layer는 경로에서 파생)
#
# 핵심 설계:
#   - 05_Inbox : 미처리·휘발성 → 인덱싱하지 않음.
#   - 06_Raw   : 불변 원본 → "전문검색 전용"으로 인덱싱한다. node+embed로 BM25/dense
#                검색은 되지만, (a) edge를 파싱하지 않고(raw 채팅 로그의
#                `[[A]] pred [[B]]` 문장이 false edge가 되는 것을 차단),
#                (b) graph_node=False라 wikilink/edge 타깃이 되지 않는다(링크는
#                source_path로만). retriever에서 낮은 가중치로 강등된다.
#   - 그 외(10/20/30/40/50/60/70/80) : 해석 계층 → node+edge 풀 인덱싱.
ALWAYS_EXCLUDE_PARTS = (
    "90_Engine", ".git", ".obsidian",
    # 가상환경·도구 디렉터리: 패키지 문서(.md)가 vault에 섞이지 않게 제외
    ".venv", "venv", "env", "ENV", ".env", "node_modules", "__pycache__", ".trash",
)

# 루트 프로젝트 메타 문서: vault 지식이 아니라 도구 설명서이므로 인덱싱 제외.
# (AGENTS.md는 제외하지 않고 retriever에서 낮은 가중치로 강등한다 — Retrieval Policy.yaml)
ROOT_DOC_EXCLUDE = ("README.md", "SETUP.md")

LAYER_POLICY = {
    "05_Inbox": {"index": False, "embed": False, "parse_edges": False,
                 "graph_node": False, "role": "inbox"},
    "06_Raw":   {"index": True,  "embed": True,  "parse_edges": False,
                 "graph_node": False, "role": "raw"},
}
DEFAULT_POLICY = {"index": True, "embed": True, "parse_edges": True,
                  "graph_node": True, "role": "knowledge"}

# 06_Raw 하위 폴더별 임베딩(dense 검색) 정책.
#   - index=True는 06_Raw 전체에 동일 적용 → embed=False여도 BM25/full-text 검색은 유지된다.
#   - embed=False는 "Ollama dense 임베딩을 만들지 않는다"는 뜻일 뿐, 검색에서 빠지는 게 아니다.
#   - parse_edges=False, graph_node=False는 06_Raw 전체에 그대로 유지(하위 폴더 무관).
#
# ⚠️ 이 정책은 **private second brain 인스턴스 기준**이다. public 템플릿에는 실제 raw가
#   절대 포함되지 않는다(README 스켈레톤만; sync guard/allowlist로 차단).
#   admin-records(행정/건강/복무/증빙/상담)는 민감하지만, 그렇기에 오히려 "나"를 잘
#   반영하는 중요한 기억이라 private 안에서 의미검색이 되도록 embed=True로 둔다.
#   이는 민감정보 임베딩이 보안상 안전하다는 뜻이 아니라, **private-only 운영을 전제로 한
#   의식적 선택**이다(유출 방지는 public/private 분리·sync guard가 담당).
RAW_SUBFOLDER_EMBED = {
    "chats":         True,
    "papers":        True,
    "project-logs":  True,
    "admin-records": True,   # 민감하지만 private-only 전제하에 의미검색 허용(의식적 선택)
    "code-logs":     False,  # 코드/에러 로그 → BM25로 충분, dense 비용 절약
    "screenshots":   False,  # OCR/캡션 → BM25로 충분
}
RAW_SUBFOLDER_EMBED_DEFAULT = False  # 분류 안 된 raw 하위 폴더/직속 파일은 BM25-only


def layer_of(path, vault_root):
    """경로의 최상위 계층 폴더명(예: '20_Concepts')을 반환. 못 찾으면 None."""
    try:
        rel = path.resolve().relative_to(Path(vault_root).resolve())
    except (ValueError, OSError):
        return None
    return rel.parts[0] if rel.parts else None


def raw_subfolder_of(path, vault_root):
    """06_Raw 직하위 폴더명(예: 'admin-records')을 반환. 폴더 없이 06_Raw 직속이면 None."""
    try:
        rel = path.resolve().relative_to(Path(vault_root).resolve())
    except (ValueError, OSError):
        return None
    # rel.parts 예: ('06_Raw', 'admin-records', 'file.md') → 하위 폴더 존재
    return rel.parts[1] if len(rel.parts) >= 3 else None


def policy_for(path, vault_root):
    """파일에 적용할 계층 정책 dict 반환 (layer 키 포함)."""
    if any(part in ALWAYS_EXCLUDE_PARTS for part in path.parts):
        return {"layer": None, "index": False, "embed": False,
                "parse_edges": False, "graph_node": False, "role": "engine"}
    layer = layer_of(path, vault_root)
    # 루트 메타 문서(README/SETUP)는 node로 만들지 않는다.
    # (루트 파일은 layer_of가 파일명을 반환하므로 layer == name 이면 vault 루트 직속)
    if path.name in ROOT_DOC_EXCLUDE and layer == path.name:
        return {"layer": layer, "index": False, "embed": False,
                "parse_edges": False, "graph_node": False, "role": "doc-excluded"}
    base = LAYER_POLICY.get(layer, DEFAULT_POLICY)
    # 06_Raw: index/edge/graph 정책은 유지하되 embed만 하위 폴더별로 차등한다.
    if layer == "06_Raw":
        sub = raw_subfolder_of(path, vault_root)
        embed = RAW_SUBFOLDER_EMBED.get(sub, RAW_SUBFOLDER_EMBED_DEFAULT)
        return {"layer": layer, **base, "embed": embed, "raw_subfolder": sub}
    return {"layer": layer, **base}


# ─────────────────────────────────────────────────────────────
# §2. Ollama 임베딩 클라이언트 (urllib 표준 라이브러리만 사용)
# ─────────────────────────────────────────────────────────────
def ollama_embed(text, model=DEFAULT_EMBED_MODEL, base_url=DEFAULT_OLLAMA_URL, timeout=30):
    """Ollama /api/embed 엔드포인트 호출. 실패 시 None 반환."""
    url = f"{base_url}/api/embed"
    payload = json.dumps({"model": model, "input": text}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        # Ollama 응답: {"embeddings": [[...]]}
        embeddings = data.get("embeddings") or data.get("embedding")
        if isinstance(embeddings, list) and embeddings:
            if isinstance(embeddings[0], list):
                return embeddings[0]  # /api/embed (배치 응답)
            return embeddings  # /api/embeddings (단일 응답)
        return None
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as e:
        return None


def normalize_vector(vec):
    """L2 정규화 — DuckDB array_cosine_similarity는 정규화된 벡터에서 dot product와 동치."""
    if not vec:
        return vec
    norm = sum(x * x for x in vec) ** 0.5
    if norm == 0:
        return vec
    return [x / norm for x in vec]


# ─────────────────────────────────────────────────────────────
# §3. 데이터베이스 초기화
# ─────────────────────────────────────────────────────────────
def init_database(db_path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(db_path))
    preds_sql = ", ".join(f"'{p}'" for p in ALLOWED_PREDICATES)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            node_id        UUID PRIMARY KEY,
            file_path      VARCHAR NOT NULL UNIQUE,
            title          VARCHAR NOT NULL,
            aliases        VARCHAR[],
            type           VARCHAR,
            moc            VARCHAR,
            md5_hash       VARCHAR NOT NULL,
            embedding      FLOAT[],
            embedding_model VARCHAR,
            embedding_hash VARCHAR,
            last_indexed   TIMESTAMP,
            updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 주의: edges.source_id/target_id에 FK(REFERENCES nodes)를 걸지 않는다.
    # DuckDB는 FK가 참조하는 부모행을 UPDATE할 때(임베딩 갱신 등) 내부적으로
    # delete+insert로 처리해 "still referenced by a foreign key" 오류를 낸다
    # (DuckDB FK 한계). 노드 임베딩/메타 UPDATE가 edge에 참조되는 순간 깨지므로
    # FK를 제거한다. 참조 무결성은 앱 레벨에서 보장한다:
    #   - indexer: title_to_id로 타깃 해석 + dangling edge skip
    #   - mcp_server: reconcile_graph()/sync_vault(force=True)로 정합
    # predicate 9-화이트리스트 CHECK과 자기참조 금지 CHECK는 유지한다.
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS edges (
            edge_id      UUID PRIMARY KEY,
            source_id    UUID,
            target_id    UUID,
            predicate    VARCHAR NOT NULL CHECK (
                predicate IN ({preds_sql})
            ),
            weight       FLOAT DEFAULT 1.0,
            evidence     VARCHAR,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CHECK (source_id != target_id)
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_predicate ON edges(predicate)")

    return conn


# ─────────────────────────────────────────────────────────────
# §4. 파싱 유틸리티
# ─────────────────────────────────────────────────────────────
def calculate_md5(content):
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def parse_yaml_frontmatter(content):
    match = FRONTMATTER_REGEX.search(content)
    if not match:
        return {}
    metadata = {}
    current_key = None
    for raw_line in match.group("meta").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line and not line.startswith("-"):
            key, _, val = line.partition(":")
            current_key = key.strip()
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                metadata[current_key] = [
                    v.strip().strip('"').strip("'")
                    for v in val[1:-1].split(",") if v.strip()
                ]
            elif val in ("null", "~", ""):
                metadata[current_key] = None
            else:
                metadata[current_key] = val.strip('"').strip("'")
        elif line.startswith("-") and current_key:
            val = line.lstrip("-").strip().strip('"').strip("'")
            if not isinstance(metadata.get(current_key), list):
                metadata[current_key] = []
            metadata[current_key].append(val)
    return metadata


def extract_edges_safely(content):
    edges = []
    in_code_block = False
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        match = EDGE_REGEX.match(stripped)
        if match:
            edges.append(match.groupdict())
    return edges


def normalize_link_target(target):
    return target.split("|", 1)[0].strip()


def strip_frontmatter_for_embedding(content):
    """임베딩용 텍스트: frontmatter 제거 + 코드 펜스 그대로 유지."""
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            return content[end + 4:].strip()
    return content


# ─────────────────────────────────────────────────────────────
# §5. 인덱싱 파이프라인
# ─────────────────────────────────────────────────────────────
def collect_markdown_files(vault_root):
    """인덱싱 대상 마크다운을 §1.5 계층 정책(policy_for)에 따라 수집한다.
    05_Inbox는 제외, 06_Raw는 전문검색 전용으로 포함된다."""
    files = []
    for path in vault_root.rglob("*.md"):
        if policy_for(path, vault_root)["index"]:
            files.append(path)
    return sorted(files)


def get_existing_node(conn, file_path):
    row = conn.execute(
        "SELECT node_id, md5_hash, embedding_model FROM nodes WHERE file_path = ?",
        [file_path]
    ).fetchone()
    if row is None:
        return None, None, None
    raw_id, stored_hash, stored_model = row
    node_uuid = raw_id if isinstance(raw_id, uuid.UUID) else uuid.UUID(str(raw_id))
    return node_uuid, stored_hash, stored_model


def index_vault(vault_root, db_path, force_rebuild=False, embed=False,
                ollama_url=DEFAULT_OLLAMA_URL, embed_model=DEFAULT_EMBED_MODEL):
    conn = init_database(db_path)
    print(f"[*] LTM Cache Engine v1.1 → {db_path}")
    print(f"[*] Vault root: {vault_root.resolve()}")
    if force_rebuild:
        print(f"[*] --force 모드: 모든 파일의 엣지를 강제 재구성")
    if embed:
        print(f"[*] --embed 모드: Ollama {embed_model} @ {ollama_url}")

    md_files = collect_markdown_files(vault_root)
    print(f"[*] 발견된 마크다운 파일: {len(md_files)}개")

    path_to_id = {}
    title_to_id = {}
    modified_paths = set()
    needs_embedding = set()
    stats = {
        "nodes_total": len(md_files),
        "nodes_new": 0,
        "nodes_updated": 0,
        "nodes_unchanged": 0,
        "embeddings_built": 0,
        "embeddings_skipped": 0,
        "embeddings_failed": 0,
        "edges_extracted": 0,
        "edges_inserted": 0,
        "edges_rejected": 0,
        "edges_dangling": 0,
    }

    # ── 1차 패스: 노드 업서트 + 임베딩 필요 판정 ──
    for path in md_files:
        content = path.read_text(encoding="utf-8")
        filename_title = path.stem
        current_hash = calculate_md5(content)
        metadata = parse_yaml_frontmatter(content)
        pol = policy_for(path, vault_root)

        existing_uuid, existing_hash, existing_model = get_existing_node(conn, str(path))

        if existing_uuid is None:
            node_uuid = uuid.uuid4()
            modified_paths.add(path)
            stats["nodes_new"] += 1
            conn.execute("""
                INSERT INTO nodes (node_id, file_path, title, aliases, type, moc, md5_hash, last_indexed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                node_uuid, str(path),
                metadata.get("title", filename_title),
                metadata.get("aliases") or [],
                metadata.get("type"),
                metadata.get("moc"),
                current_hash,
                datetime.now(),
            ])
            if embed and pol["embed"]:
                needs_embedding.add((node_uuid, path, content))
        elif existing_hash != current_hash:
            node_uuid = existing_uuid
            modified_paths.add(path)
            stats["nodes_updated"] += 1
            conn.execute("""
                UPDATE nodes SET title = ?, aliases = ?, type = ?, moc = ?,
                    md5_hash = ?, last_indexed = ?, updated_at = CURRENT_TIMESTAMP
                WHERE node_id = ?
            """, [
                metadata.get("title", filename_title),
                metadata.get("aliases") or [],
                metadata.get("type"),
                metadata.get("moc"),
                current_hash,
                datetime.now(),
                node_uuid,
            ])
            if embed and pol["embed"]:
                needs_embedding.add((node_uuid, path, content))
        else:
            node_uuid = existing_uuid
            stats["nodes_unchanged"] += 1
            if force_rebuild:
                modified_paths.add(path)
            # 임베딩 모델이 바뀌었거나 임베딩이 없는 경우에만 재임베딩
            if embed and pol["embed"] and existing_model != embed_model:
                needs_embedding.add((node_uuid, path, content))
            elif embed and pol["embed"] and force_rebuild:
                needs_embedding.add((node_uuid, path, content))

        path_to_id[path] = node_uuid
        # graph_node인 계층만 링크 네임스페이스(title_to_id)에 등록한다.
        # 06_Raw 등 full-text 전용 node는 wikilink/edge 타깃이 되지 않으므로 제외
        # → raw 파일명이 우연히 개념 edge의 타깃으로 해석되는 것을 막는다.
        if pol["graph_node"]:
            title_to_id[filename_title] = node_uuid
            for alias in (metadata.get("aliases") or []):
                title_to_id.setdefault(alias, node_uuid)

    print(f"[*] 노드 패스 완료 — 신규: {stats['nodes_new']}, 수정: {stats['nodes_updated']}, 무변경: {stats['nodes_unchanged']}")

    # ── 1.5차 패스: 임베딩 빌드 ──
    if embed and needs_embedding:
        print(f"[*] 임베딩 빌드 시작: {len(needs_embedding)}개 노드")
        for i, (node_uuid, path, content) in enumerate(sorted(needs_embedding, key=lambda x: str(x[1])), 1):
            text_for_embed = strip_frontmatter_for_embedding(content)
            vec = ollama_embed(text_for_embed, model=embed_model, base_url=ollama_url)
            if vec is None:
                stats["embeddings_failed"] += 1
                if stats["embeddings_failed"] <= 2:
                    print(f"  [WARN] {path.name}: Ollama 응답 실패 (BM25-only로 fallback 예정)")
                continue
            normalized = normalize_vector(vec)
            emb_hash = hashlib.md5(json.dumps(normalized[:8]).encode()).hexdigest()
            conn.execute("""
                UPDATE nodes
                SET embedding = ?, embedding_model = ?, embedding_hash = ?
                WHERE node_id = ?
            """, [normalized, embed_model, emb_hash, node_uuid])
            stats["embeddings_built"] += 1
            if i % 5 == 0 or i == len(needs_embedding):
                print(f"  [*] 진행: {i}/{len(needs_embedding)}")

        print(f"[*] 임베딩 패스 완료 — 빌드: {stats['embeddings_built']}, 실패: {stats['embeddings_failed']}")

    # ── 2차 패스: 엣지 재구성 ──
    for path in modified_paths:
        # parse_edges=False 계층(06_Raw 등)은 edge를 파싱하지 않는다.
        # raw 채팅 로그의 `[[A]] pred [[B]]` 문장이 false edge가 되는 것을 차단.
        if not policy_for(path, vault_root)["parse_edges"]:
            continue
        file_source_uuid = path_to_id[path]
        conn.execute("DELETE FROM edges WHERE source_id = ?", [file_source_uuid])
        content = path.read_text(encoding="utf-8")
        raw_edges = extract_edges_safely(content)
        stats["edges_extracted"] += len(raw_edges)

        for edge in raw_edges:
            predicate = edge["predicate"]
            target_title = normalize_link_target(edge["target"])
            source_title = normalize_link_target(edge["source"])

            if predicate not in ALLOWED_PREDICATES:
                print(f"  [REJECT] {path.name}: 화이트리스트 외 술어 '{predicate}'")
                stats["edges_rejected"] += 1
                continue

            source_uuid = title_to_id.get(source_title)
            target_uuid = title_to_id.get(target_title)

            if source_uuid is None or target_uuid is None:
                stats["edges_dangling"] += 1
                continue

            if source_uuid == target_uuid:
                print(f"  [REJECT] {path.name}: 자기참조")
                stats["edges_rejected"] += 1
                continue

            try:
                conn.execute("""
                    INSERT INTO edges (edge_id, source_id, target_id, predicate, evidence)
                    VALUES (?, ?, ?, ?, ?)
                """, [
                    uuid.uuid4(), source_uuid, target_uuid, predicate, edge.get("desc"),
                ])
                stats["edges_inserted"] += 1
            except Exception as e:
                print(f"  [ERROR] {path.name}: {e}")
                stats["edges_rejected"] += 1

    conn.commit()
    return stats, conn


# ─────────────────────────────────────────────────────────────
# §6. 리포트
# ─────────────────────────────────────────────────────────────
def print_report(conn, stats):
    print()
    print("=" * 64)
    print("  Karpathy LLM Framework - Vault 인덱싱 리포트 v1.1")
    print("=" * 64)
    print(f"\n[노드] 총 {stats['nodes_total']} | 신규 {stats['nodes_new']} | 수정 {stats['nodes_updated']} | 무변경 {stats['nodes_unchanged']}")
    print(f"[엣지] 추출 {stats['edges_extracted']} | 적재 {stats['edges_inserted']} | 거부 {stats['edges_rejected']} | Dangling {stats['edges_dangling']}")
    print(f"[임베딩] 빌드 {stats['embeddings_built']} | 실패 {stats['embeddings_failed']}")

    print(f"\n[술어 분포]")
    rows = conn.execute("""
        SELECT predicate, COUNT(*) AS cnt FROM edges
        GROUP BY predicate ORDER BY cnt DESC
    """).fetchall()
    for pred, cnt in rows:
        print(f"  {pred:18s} {cnt:3d}  {'█' * cnt}")

    cov = conn.execute("""
        SELECT COUNT(*) AS total, COUNT(embedding) AS with_emb,
               COUNT(DISTINCT embedding_model) AS model_cnt
        FROM nodes
    """).fetchone()
    print(f"\n[임베딩 커버리지] {cov[1]}/{cov[0]} 노드 ({100*cov[1]//max(cov[0],1)}%)")

    print(f"\n[Hub Top 5]")
    rows = conn.execute("""
        SELECT n.title, COUNT(e.edge_id) AS deg FROM nodes n
        LEFT JOIN edges e ON e.target_id = n.node_id
        GROUP BY n.title ORDER BY deg DESC, n.title LIMIT 5
    """).fetchall()
    for title, deg in rows:
        print(f"  {title:40s} ← {deg}")

    print()
    print("=" * 64)


def main():
    parser = argparse.ArgumentParser(description="Karpathy LLM Framework Vault Indexer v1.1")
    parser.add_argument("--vault", default=".", help="Vault 루트 경로")
    parser.add_argument("--db", default="90_Engine/ltm_cache.db", help="DuckDB 캐시 경로")
    parser.add_argument("--report", action="store_true", help="리포트 출력")
    parser.add_argument("--force", action="store_true", help="MD5 무관 모든 파일 엣지 재구성")
    parser.add_argument("--embed", action="store_true", help="Ollama 임베딩 빌드/캐시")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL, help="Ollama 베이스 URL")
    parser.add_argument("--ollama-model", default=DEFAULT_EMBED_MODEL, help="임베딩 모델명")
    args = parser.parse_args()

    vault_root = Path(args.vault).resolve()
    db_path = Path(args.db)
    if not db_path.is_absolute():
        db_path = vault_root / args.db

    stats, conn = index_vault(
        vault_root, db_path,
        force_rebuild=args.force,
        embed=args.embed,
        ollama_url=args.ollama_url,
        embed_model=args.ollama_model,
    )
    if args.report:
        print_report(conn, stats)
    conn.close()
    print("[+] 인덱싱 파이프라인 완료.")


if __name__ == "__main__":
    main()
