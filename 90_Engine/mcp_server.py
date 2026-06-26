#!/usr/bin/env python3
"""
90_Engine/mcp_server.py
Karpathy LLM Framework - MCP Server (stdio transport) v3.0  [AI-managed LTM · 단일 소유자 데몬 프록시]

원본 v1.0의 읽기 도구(retrieve_knowledge / sync_vault / vault_stats)에
AI가 그래프를 직접 관리할 수 있는 write 도구를 추가한 버전.

추가된 write 도구:
  - create_node(...)   : 새 메모리 node 생성 + 엣지 + 자동 임베딩
  - update_node(...)   : 기존 node 본문/엣지 수정 (정체성 node_id 보존)
  - upsert_edge(...)   : 기존 node에 엣지 1개 추가
  - remove_edge(...)   : 기존 node에서 엣지 1개 제거
  - delete_node(...)   : node 파일 + DB node/엣지 안전 삭제
  - reconcile_graph()  : 전체 엣지 재구성으로 dangling 일괄 해소(주기 실행 권장)
  - list_nodes()       : 전체 node 목록(링크 타깃 선택용)

설계 원칙:
  * 메모리는 마크다운 파일로 작성되고, indexer가 단일 게이트키퍼로
    9술어 CHECK 제약 검증 + UUID 발급 + Ollama 임베딩을 담당한다.
  * 이 서버는 **단일 소유자 데몬(vault_daemon.py)의 얇은 프록시**다. 읽기/인덱싱은
    localhost HTTP로 데몬에 포워딩하고(데몬만 DuckDB를 만진다), 쓰기 도구는 "규격에 맞는
    마크다운을 쓰고 → 데몬 /reindex를 트리거"한다. 데몬은 첫 요청에 자동 기동되며, 닿지
    못하면 in-process 폴백 없이 명확한 에러를 낸다(split-brain·락경합 방지).
  * write 도구는 기본 증분 인덱싱(빠름)만 한다. 새 node가 '기존 node로부터' 받는 링크는
    즉시 연결되지 않으므로, reconcile_graph()(또는 sync_vault(force=True))를 주기적으로
    실행해 그래프를 정합한다(대규모 vault도 재임베딩 없어 저비용).
  * 링크/엣지 타깃은 반드시 대상 node의 '제목(=파일명 stem)'과 정확히 일치해야 한다.
  * predicate는 9개 화이트리스트만 허용. 그 외는 거부된다.

Cursor / Claude Desktop / Antigravity 설정 (~/.cursor/mcp.json 등):
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
"""

import os
import re
import sys
import uuid
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    sys.exit("ERROR: mcp 미설치. pip install mcp --break-system-packages")

# 같은 디렉터리의 indexer 모듈을 import (frontmatter 파싱). DB 접근은 데몬이 전담한다.
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

import indexer as indexer_mod
import daemon_client


# ─────────────────────────────────────────────────────────────
# 환경 변수 (MCP 클라이언트의 config.env에서 주입)
# ─────────────────────────────────────────────────────────────
VAULT_ROOT = os.environ.get("VAULT_ROOT", str(SCRIPT_DIR.parent))
VAULT_DB = os.environ.get("VAULT_DB", str(SCRIPT_DIR / "ltm_cache.db"))
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "bge-m3")

# 읽기/쓰기 모두 단일 소유자 데몬으로 포워딩한다(데몬이 표준). 데몬은 첫 요청에 자동
# 기동되며, 닿지 못하면 in-process 폴백 대신 명확한 에러를 낸다(split-brain·락경합 방지).
_daemon_port_cache = None      # 최근 확인된 정상 데몬 포트(있으면 ensure/health 생략)
_daemon_retry_after = 0.0      # 네거티브 캐시: 이 시각 전엔 ensure_daemon 재시도 안 함


def _daemon_env() -> dict:
    """스폰될 데몬이 프록시와 '동일한' vault/모델을 쓰도록 명시 env 전달
    (호스트 env 타이밍/기본값 차이로 포트·DB가 갈리는 것 방지)."""
    env = dict(os.environ)
    env.update(VAULT_DB=VAULT_DB, VAULT_ROOT=VAULT_ROOT,
               OLLAMA_URL=OLLAMA_URL, OLLAMA_MODEL=OLLAMA_MODEL)
    return env


def _get_daemon_port():
    """정상 데몬 포트 또는 None. known-good는 캐시(매 호출 /health·spawn 생략),
    기동 실패는 30초 네거티브 캐시(포트 충돌 시 매 호출 ~20s 스폰 폭주 방지)."""
    global _daemon_port_cache, _daemon_retry_after
    if _daemon_port_cache:
        return _daemon_port_cache
    if time.time() < _daemon_retry_after:
        return None
    port = daemon_client.ensure_daemon(VAULT_DB, SCRIPT_DIR, env=_daemon_env())
    if port:
        _daemon_port_cache = port
        return port
    _daemon_retry_after = time.time() + 30.0
    return None


def _daemon(method: str, path: str, payload: dict = None, timeout: float = 120.0):
    """데몬으로 포워딩하고 결과를 반환한다. 데몬에 닿지 못하면 RuntimeError(폴백 없음).
    데몬은 첫 요청에 자동 기동된다(daemon_client.ensure_daemon). timeout은 GET/POST 모두에
    적용한다 — 요청 경로의 _maybe_pull이 git pull을 돌 수 있어 read에도 넉넉한 기본값을 둔다."""
    global _daemon_port_cache
    port = _get_daemon_port()
    if not port:
        raise RuntimeError(
            "vault 데몬에 연결할 수 없습니다. 의존성(fastapi/uvicorn/pydantic)이 venv에 "
            "설치됐는지 확인하고, DAEMON_DEBUG=1로 90_Engine/daemon.spawn.log를 보세요. "
            "(See handoff/DAEMON_SPAWN_FIX.md)"
        )
    try:
        if method == "GET":
            return daemon_client.get(port, path, timeout=timeout)
        return daemon_client.post(port, path, payload or {}, timeout=timeout)
    except Exception as e:
        _daemon_port_cache = None  # 호출 실패 → 캐시 무효화(다음 호출이 재확인/재기동)
        raise RuntimeError(f"데몬 호출 실패({path}): {e}") from e

# 링크/편집 네임스페이스 제외 목록. list_nodes()와 _find_node_path()가 사용한다.
# 05_Inbox/06_Raw는 wikilink/edge 타깃이 아니라 source_path로만 참조되므로 여기서 제외.
# 주의: 이는 "검색 인덱싱" 제외와 다르다. indexer는 06_Raw를 full-text 전용으로
# 인덱싱(검색 가능)하되 graph_node=False라 링크 타깃은 아니다. 즉 이 목록과
# indexer의 policy_for(graph_node=False)는 일관된다. 05_Inbox만 완전 제외.
EXCLUDE_PARTS = ("90_Engine", ".git", ".obsidian", "05_Inbox", "06_Raw",
                 ".venv", "venv", "env", "ENV", ".env", "node_modules",
                 "__pycache__", ".trash")
EDGE_HEADING = "## 핵심 엣지"
EMPTY_EDGE_PLACEHOLDER = "<!-- 아직 엣지 없음 -->"


# ─────────────────────────────────────────────────────────────
# 내부 헬퍼
# ─────────────────────────────────────────────────────────────
def _vault_root() -> Path:
    return Path(VAULT_ROOT).resolve()


def _run_indexer(force: bool = False, embed: bool = True) -> dict:
    """DB 인덱싱을 단일 소유자 데몬의 /reindex로 위임한다(데몬만 DB를 만진다).
    데몬에 닿지 못하면 에러 — split-brain 방지로 in-process 폴백은 없다."""
    return _daemon("POST", "/reindex", {"force": force, "embed": embed}, timeout=900)


def _validate_title(title: str) -> str:
    t = (title or "").strip()
    if not t:
        raise ValueError("title이 비어 있습니다.")
    bad = set('\\/:*?"<>|')
    if any(c in bad for c in t):
        raise ValueError(f"title에 파일명 금지문자(\\ / : * ? \" < > |)가 있습니다: {t!r}")
    if t.startswith("."):
        raise ValueError("title은 '.'으로 시작할 수 없습니다.")
    return t


def _find_node_path(title: str) -> Optional[Path]:
    """제목(=파일명 stem)으로 node 파일을 찾는다. 엔진/숨김 폴더는 제외."""
    root = _vault_root()
    for p in root.rglob(f"{title}.md"):
        if any(part in EXCLUDE_PARTS for part in p.parts):
            continue
        return p
    return None


def _validate_edges(title: str, edges) -> list:
    """edges: [{"predicate","target","description?"}] → [(pred, target, desc)] 검증."""
    out = []
    for e in (edges or []):
        if not isinstance(e, dict):
            raise ValueError("각 edge는 {predicate, target, description?} 형태의 dict여야 합니다.")
        pred = (e.get("predicate") or "").strip()
        tgt = (e.get("target") or "").strip()
        desc = e.get("description")
        if pred not in indexer_mod.ALLOWED_PREDICATES:
            raise ValueError(
                f"허용되지 않은 predicate {pred!r}. 9개만 허용: "
                f"{', '.join(indexer_mod.ALLOWED_PREDICATES)}"
            )
        if not tgt:
            raise ValueError("edge의 target이 비어 있습니다.")
        if tgt == title:
            raise ValueError(f"자기참조 edge는 금지입니다: {title!r}")
        out.append((pred, tgt, desc))
    return out


def _dangling_warnings(edges) -> list:
    w = []
    for (pred, tgt, _desc) in edges:
        if _find_node_path(tgt) is None:
            w.append(
                f"target '{tgt}' node가 아직 없어 dangling 상태입니다. "
                f"create_node로 만들면 다음 sync에서 자동 연결됩니다."
            )
    return w


def _edge_line(src: str, pred: str, tgt: str, desc: Optional[str] = None) -> str:
    line = f"- `[[{src}]] {pred} [[{tgt}]]`"
    if desc:
        line += f" — {desc}"
    return line


def _build_node_markdown(title, body, type_, moc, aliases, tags, edges, sources,
                         node_id=None, id_=None, created=None, version="1.0") -> str:
    """indexer가 파싱 가능한 frontmatter + 9술어 엣지 섹션을 갖춘 node 생성.

    edges: [(pred, target, desc)] (source는 title로 고정)
    """
    nid = node_id or str(uuid.uuid4())
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_") or "node"
    idv = id_ or f"concept_{slug}"
    created = created or datetime.now().strftime("%Y-%m-%d")
    al = "[" + ", ".join(aliases) + "]" if aliases else "[]"
    tg = "[" + ", ".join(tags) + "]" if tags else "[]"
    moc_line = f'moc: "[[{moc}]]"' if moc else "moc:"

    out = [
        "---",
        f"id: {idv}",
        f"title: {title}",
        f"aliases: {al}",
        f"type: {type_ or 'Concept'}",
        moc_line,
        f"tags: {tg}",
        "status: draft",
        f"created: {created}",
        f"version: {version}",
        f"node_id: {nid}",
        "---",
        "",
        f"# {title}",
        "",
        (body or "").strip(),
        "",
        EDGE_HEADING,
        "",
    ]
    if edges:
        for (pred, tgt, desc) in edges:
            out.append(_edge_line(title, pred, tgt, desc))
    else:
        out.append(EMPTY_EDGE_PLACEHOLDER)
    out += ["", "## Sources", ""]
    for s in (sources or []):
        out.append(f"- {s}")
    out.append("")
    return "\n".join(out)


def _insert_edge_line(text: str, line: str) -> str:
    """'## 핵심 엣지' 섹션에 엣지 라인을 삽입. 섹션이 없으면 Sources 앞/끝에 생성."""
    lines = text.splitlines()
    hidx = next((i for i, l in enumerate(lines) if l.strip() == EDGE_HEADING), None)
    if hidx is not None:
        insert = hidx + 1
        if insert < len(lines) and lines[insert].strip() == "":
            insert += 1
        if insert < len(lines) and lines[insert].strip() == EMPTY_EDGE_PLACEHOLDER:
            lines.pop(insert)
        lines.insert(insert, line)
        return "\n".join(lines) + "\n"
    block = ["", EDGE_HEADING, "", line]
    sidx = next((i for i, l in enumerate(lines) if l.strip() == "## Sources"), None)
    if sidx is not None:
        lines[sidx:sidx] = block + [""]
    else:
        lines += block
    return "\n".join(lines) + "\n"


def _norm(t: str) -> str:
    return indexer_mod.normalize_link_target(t)


# ─────────────────────────────────────────────────────────────
# MCP 서버 정의
# ─────────────────────────────────────────────────────────────
mcp = FastMCP(
    "karpathy-vault-ltm",
    instructions=(
        "이 서버는 장기기억(LTM) 지식 그래프 vault입니다. Claude Code의 memory를 "
        "쓰듯 능동적으로 활용하세요. vault의 문서 하나하나가 곧 memory node입니다.\n"
        "- 지식·개념·과거 결정·출처에 관한 질문에 답하기 전에, 먼저 "
        "retrieve_knowledge 로 vault를 조회해 관련 node/엣지를 확인합니다.\n"
        "- 새로운 사실·결정·정의가 확정되면 create_node(필요 시 upsert_edge)로 "
        "기록하고, 기존 node가 바뀌면 update_node 로 갱신합니다.\n"
        "- vault 파일이 외부에서 변경되었을 수 있으면 sync_vault 로 동기화한 뒤 "
        "조회합니다.\n"
        "- 검증·정리가 필요하면 review_queue / reconcile_graph 로 상태를 점검합니다.\n"
        "raw 원본(06_Raw)은 그래프 node가 아니라 검색 전용이며, 그래프 대리물은 "
        "50_Source_Summaries 의 source-summary node입니다."
    ),
)


# ===== 읽기 도구 (원본 유지) ===============================================
@mcp.tool()
def retrieve_knowledge(query: str, top_k: int = 5, max_hops: int = 2,
                       max_nodes: int = 10, include_raw: bool = True,
                       include_reviews: bool = False,
                       confidence_weighting: bool = True) -> dict:
    """Vault에서 자연어 쿼리에 가장 의미적으로 가까운 지식 서브그래프를 검색하여
    하이브리드 캡슐 포맷(JSON 메타 + XML 감싼 마크다운 본문)으로 반환합니다.

    9개 술어 그래프 위에서 BM25 + Dense embedding을 RRF로 결합해 seed nodes를
    찾고, Adaptive 2-hop graph expansion으로 의미 서브그래프를 확장합니다.

    [계층/신뢰도 인지] 검증된 지식 계층(20_Concepts/50_Source_Summaries 등)은
    높게, 원본(06_Raw, full-text 전용)·낮은 신뢰도·폐기 상태는 낮게 랭크됩니다.
    검토/메타 계층(60/70/80)은 기본 검색에서 제외됩니다(include_reviews=True로 포함).
    결과 JSON의 각 node에는 layer/confidence/status가 함께 표기되어, 출처와
    불확실성을 직접 판단할 수 있습니다.

    Args:
        query: 자연어 질문 (한국어/영어 혼합 가능)
        top_k: 1차 검색 seed nodes 수 (기본 5)
        max_hops: 그래프 확장 최대 hop (기본 2)
        max_nodes: 출력 캡슐 최대 node 수 (기본 10)
        include_raw: 06_Raw 원본(full-text 전용)을 후보에 포함 (기본 True, 강등됨)
        include_reviews: 60/70/80 검토·메타 계층 포함 (기본 False)
        confidence_weighting: confidence(low/medium) 강등 적용 (기본 True)

    """
    return _daemon("POST", "/retrieve", {
        "query": query, "top_k": top_k, "max_hops": max_hops, "max_nodes": max_nodes,
        "include_raw": include_raw, "include_reviews": include_reviews,
        "confidence_weighting": confidence_weighting,
    })


@mcp.tool()
def sync_vault(force: bool = False, embed: bool = True) -> dict:
    """Vault 디렉터리를 스캔하여 신규/수정된 Markdown node를 DuckDB로 증분 컴파일.

    MD5로 변경을 감지해 무변경 파일은 건너뜁니다. embed=True면 변경 node만 Ollama로
    재임베딩합니다. dangling edge(타깃 node가 뒤늦게 생긴 경우 등)를 모두 다시
    풀고 싶으면 force=True로 호출하세요(엣지 전체 재구성).

    Args:
        force: True면 MD5 무관 모든 파일의 엣지 강제 재구성
        embed: True면 Ollama 임베딩 빌드 (Ollama 미가동 시 graceful skip)
    """
    return _run_indexer(force=force, embed=embed)


@mcp.tool()
def vault_stats() -> dict:
    """현재 Vault 그래프 통계: node/엣지 수, 임베딩 커버리지, 술어 분포,
    Hub Top 5(in-degree), Authority Top 5(out-degree)."""
    return _daemon("GET", "/vault_stats")


# ===== 검토 큐 위생 도구 ====================================================
REVIEW_QUEUE_DIRS = ("60_Open_Questions", "70_Contradictions", "80_Reviews")
_REVIEW_ITEM_RE = re.compile(r"^###\s*\[(?P<status>[A-Za-z\-]+)\]\s*(?P<title>.+?)\s*$")


@mcp.tool()
def review_queue(status: str = "open", layer: Optional[str] = None) -> dict:
    """검토·질문·모순 큐(60/70/80)에서 항목을 모아 상태별로 반환합니다.

    각 큐 파일의 `### [status] 제목` 항목과 파일 frontmatter(type/reason/category)를
    스캔합니다. 검토 큐가 쌓이기만 하고 비워지지 않는 것을 막기 위한 위생 도구입니다.
    (검토 카테고리/상태 정의는 00_System/Review Policy.md)

    Args:
        status: 필터할 항목 상태 (open/reviewed/resolved/rejected/superseded).
                "all"이면 전체.
        layer: 특정 계층만 (예: "80_Reviews"). None이면 60/70/80 전체.

    Returns:
        {count, status_filter, files:[{path, layer, file_type, items:[{status,title}]}],
         items:[{layer, file, status, title}]}
    """
    root = _vault_root()
    want = (status or "open").strip().lower()
    dirs = (layer,) if layer else REVIEW_QUEUE_DIRS
    files_out, items_flat = [], []
    for d in dirs:
        base = root / d
        if not base.exists():
            continue
        for p in sorted(base.rglob("*.md")):
            if any(part in EXCLUDE_PARTS for part in p.parts):
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except Exception:
                continue
            meta = indexer_mod.parse_yaml_frontmatter(text)
            items = []
            in_code = False
            for line in text.splitlines():
                st = line.strip()
                if st.startswith("```"):
                    in_code = not in_code
                    continue
                if in_code:
                    continue
                m = _REVIEW_ITEM_RE.match(st)
                if m:
                    s = m.group("status").lower()
                    if want == "all" or s == want:
                        item = {"status": s, "title": m.group("title")}
                        items.append(item)
                        items_flat.append({
                            "layer": d, "file": str(p.relative_to(root)),
                            "status": s, "title": m.group("title"),
                        })
            files_out.append({
                "path": str(p.relative_to(root)),
                "layer": d,
                "file_type": meta.get("type"),
                "reason": meta.get("reason"),
                "category": meta.get("category"),
                "open_items": len(items),
                "items": items,
            })
    return {
        "count": len(items_flat),
        "status_filter": want,
        "files": files_out,
        "items": items_flat,
    }


# ===== 쓰기 도구 (신규) ====================================================
@mcp.tool()
def list_nodes() -> dict:
    """Vault의 모든 node 목록을 반환합니다. 엣지를 연결하기 전에 호출하여
    정확한 링크 타깃(=node 제목)을 확인하세요. dangling edge를 예방하는 핵심 도구.

    Returns:
        {count, notes: [{title, type, moc, path}]}
        title이 곧 링크/엣지에서 [[...]]에 써야 하는 정확한 문자열입니다.
    """
    root = _vault_root()
    out = []
    for p in sorted(root.rglob("*.md")):
        if any(part in EXCLUDE_PARTS for part in p.parts):
            continue
        try:
            meta = indexer_mod.parse_yaml_frontmatter(p.read_text(encoding="utf-8"))
        except Exception:
            meta = {}
        out.append({
            "title": p.stem,
            "type": meta.get("type"),
            "moc": meta.get("moc"),
            "path": str(p.relative_to(root)),
        })
    return {"count": len(out), "notes": out}


@mcp.tool()
def create_node(title: str, body: str, type: str = "Concept",
                moc: Optional[str] = None, aliases: Optional[list] = None,
                tags: Optional[list] = None, edges: Optional[list] = None,
                sources: Optional[list] = None, folder: str = "20_Concepts",
                embed: bool = True, resolve_links: bool = False) -> dict:
    """새 메모리 node를 생성합니다. 온톨로지 규격에 맞는 마크다운을 작성하고
    indexer를 트리거하여 UUID 발급·임베딩·9술어 검증까지 자동 수행합니다.

    ⚠️ 규칙:
      - 파일은 '{title}.md'로 저장되며 title이 곧 다른 node가 링크할 식별자입니다.
        제목은 명사형 단일 엔티티로, 파일명 금지문자를 쓰지 마세요.
      - edges의 각 target은 '이미 존재하거나 곧 만들 node의 정확한 제목'이어야 합니다.
        먼저 list_nodes()로 타깃 제목을 확인하면 dangling을 피할 수 있습니다.
      - predicate는 9개만 허용: requires, utilizes, implemented_by, extends,
        abstracts, causes, contradicts, replaces, defines.

    Args:
        title: node 제목(=파일명, =링크 식별자)
        body: 본문 마크다운 (정의 3문장 + 핵심 메커니즘 등)
        type: node 타입 (기본 "Concept")
        moc: 소속 MOC 제목 (예: "Philosophy MOC"). 자동으로 [[..]]로 감쌈
        aliases: 별칭 리스트
        tags: 태그 리스트
        edges: [{"predicate","target","description"}] 리스트. source는 이 node로 고정
        sources: 출처 문자열 리스트
        folder: 저장 폴더 (기본 "20_Concepts")
        embed: True면 생성 즉시 Ollama 임베딩 (Ollama 미가동 시 BM25-only)
        resolve_links: True면 전체 엣지 재구성으로 '기존 node→이 node' dangling까지
            즉시 연결. 기본 False(빠름). 평소엔 reconcile_graph()를 주기 실행 권장.

    Returns:
        {created, title, edges_added, nodes_new, embeddings_built,
         edges_inserted, edges_dangling, resolved_links, warnings}
    """
    title = _validate_title(title)
    if _find_node_path(title) is not None:
        raise ValueError(
            f"이미 '{title}' node가 존재합니다. 수정하려면 update_node를 사용하세요."
        )
    norm_edges = _validate_edges(title, edges)
    md = _build_node_markdown(
        title, body, type, moc, aliases or [], tags or [], norm_edges, sources or []
    )
    note_path = _vault_root() / folder / f"{title}.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(md, encoding="utf-8")

    # 증분 인덱싱: 신규 node 임베딩 + 자기 엣지 구성 (빠름)
    stats = _run_indexer(force=False, embed=embed)
    # 이 node를 향하던 '기존' dangling edge까지 즉시 잇고 싶을 때만 전체 재구성
    if resolve_links:
        stats = _run_indexer(force=True, embed=False)

    warnings = _dangling_warnings(norm_edges)
    if not resolve_links and warnings:
        warnings.append("기존 node가 이 node를 링크 중이라면 reconcile_graph()로 정합하세요.")
    return {
        "created": str(note_path),
        "title": title,
        "edges_added": len(norm_edges),
        "nodes_new": stats.get("nodes_new"),
        "embeddings_built": stats.get("embeddings_built"),
        "edges_inserted": stats.get("edges_inserted"),
        "edges_dangling": stats.get("edges_dangling"),
        "resolved_links": resolve_links,
        "warnings": warnings,
    }


@mcp.tool()
def update_node(title: str, body: Optional[str] = None, edges: Optional[list] = None,
                type: Optional[str] = None, moc: Optional[str] = None,
                aliases: Optional[list] = None, tags: Optional[list] = None,
                sources: Optional[list] = None, embed: bool = True,
                resolve_links: bool = False) -> dict:
    """기존 node의 본문/엣지/메타를 수정합니다. node_id·id·created 등 정체성은 보존합니다.

    인자를 주지 않은 항목은 기존 값을 유지합니다(예: body만 주면 엣지는 그대로).
    edges를 주면 엣지 섹션을 '통째로 교체'합니다(부분 추가는 upsert_edge 사용).

    Args:
        title: 수정할 node 제목
        body: 새 본문(주지 않으면 기존 intro 본문 유지)
        edges: 새 엣지 전체 [{"predicate","target","description"}] (주면 교체)
        type, moc, aliases, tags, sources: 주면 해당 메타만 갱신
        embed: True면 변경 후 재임베딩
    """
    title = _validate_title(title)
    path = _find_node_path(title)
    if path is None:
        raise ValueError(f"'{title}' node를 찾을 수 없습니다. 새로 만들려면 create_node를 쓰세요.")
    old = path.read_text(encoding="utf-8")
    meta = indexer_mod.parse_yaml_frontmatter(old)

    # 기존 본문(intro) 추출: frontmatter 이후 ~ 첫 '## ' 이전, 선두 H1 제거
    after = old
    m = indexer_mod.FRONTMATTER_REGEX.search(old)
    if m:
        after = old[m.end():]
    intro = after.split("\n## ", 1)[0].strip()
    intro_lines = intro.splitlines()
    if intro_lines and intro_lines[0].lstrip().startswith("# "):
        intro_lines = intro_lines[1:]
    existing_body = "\n".join(intro_lines).strip()

    # 기존 엣지 추출 (코드블록 안전)
    existing_edges = [
        (e["predicate"], _norm(e["target"]), e.get("desc"))
        for e in indexer_mod.extract_edges_safely(old)
        if _norm(e["source"]) == title
    ]

    # 기존 sources 추출
    existing_sources = []
    if "## Sources" in after:
        src_block = after.split("## Sources", 1)[1]
        for l in src_block.splitlines():
            ls = l.strip()
            if ls.startswith("## "):
                break
            if ls.startswith("- "):
                existing_sources.append(ls[2:].strip())

    new_edges = _validate_edges(title, edges) if edges is not None else existing_edges
    new_body = body if body is not None else existing_body
    new_type = type if type is not None else meta.get("type")
    new_moc = moc if moc is not None else (
        _norm(meta.get("moc")).strip("[]") if meta.get("moc") else None
    )
    new_aliases = aliases if aliases is not None else (meta.get("aliases") or [])
    new_tags = tags if tags is not None else (meta.get("tags") or [])
    new_sources = sources if sources is not None else existing_sources

    md = _build_node_markdown(
        title, new_body, new_type, new_moc, new_aliases, new_tags,
        new_edges, new_sources,
        node_id=meta.get("node_id"), id_=meta.get("id"), created=meta.get("created"),
    )
    path.write_text(md, encoding="utf-8")

    stats = _run_indexer(force=False, embed=embed)
    if resolve_links:
        stats = _run_indexer(force=True, embed=False)
    return {
        "updated": str(path),
        "title": title,
        "edges_total": len(new_edges),
        "embeddings_built": stats.get("embeddings_built"),
        "edges_dangling": stats.get("edges_dangling"),
        "resolved_links": resolve_links,
        "warnings": _dangling_warnings(new_edges),
    }


@mcp.tool()
def upsert_edge(source_title: str, predicate: str, target_title: str,
                description: Optional[str] = None) -> dict:
    """기존 source node에 엣지 1개를 추가합니다(이미 있으면 무시).

    엣지는 항상 source node의 파일에 기록됩니다(indexer가 source 단위로 엣지를
    재구성하기 때문). 따라서 source_title node가 반드시 존재해야 합니다.

    Args:
        source_title: 엣지를 추가할 node 제목 (존재해야 함)
        predicate: 9개 화이트리스트 중 하나
        target_title: 대상 node 제목 (없으면 dangling 경고)
        description: 관계 설명(선택)
    """
    src = _validate_title(source_title)
    if predicate not in indexer_mod.ALLOWED_PREDICATES:
        raise ValueError(
            f"허용되지 않은 predicate {predicate!r}. 9개만 허용: "
            f"{', '.join(indexer_mod.ALLOWED_PREDICATES)}"
        )
    tgt = (target_title or "").strip()
    if not tgt:
        raise ValueError("target_title이 비어 있습니다.")
    if tgt == src:
        raise ValueError("자기참조 edge는 금지입니다.")
    path = _find_node_path(src)
    if path is None:
        raise ValueError(f"source node '{src}'를 찾을 수 없습니다. 먼저 create_node로 만드세요.")

    text = path.read_text(encoding="utf-8")
    for e in indexer_mod.extract_edges_safely(text):
        if (e["predicate"] == predicate and _norm(e["target"]) == tgt
                and _norm(e["source"]) == src):
            return {"status": "exists", "edge": f"[[{src}]] {predicate} [[{tgt}]]"}

    new_text = _insert_edge_line(text, _edge_line(src, predicate, tgt, description))
    path.write_text(new_text, encoding="utf-8")
    stats = _run_indexer(force=False, embed=False)
    return {
        "status": "added",
        "edge": f"[[{src}]] {predicate} [[{tgt}]]",
        "edges_inserted": stats.get("edges_inserted"),
        "edges_dangling": stats.get("edges_dangling"),
        "warnings": _dangling_warnings([(predicate, tgt, description)]),
    }


@mcp.tool()
def remove_edge(source_title: str, predicate: str, target_title: str) -> dict:
    """기존 source node에서 특정 엣지 라인을 제거합니다.

    Args:
        source_title: 엣지가 기록된 node 제목
        predicate: 제거할 엣지의 술어
        target_title: 제거할 엣지의 대상 제목
    """
    src = _validate_title(source_title)
    tgt = (target_title or "").strip()
    path = _find_node_path(src)
    if path is None:
        raise ValueError(f"source node '{src}'를 찾을 수 없습니다.")
    lines = path.read_text(encoding="utf-8").splitlines()
    kept, removed = [], 0
    for l in lines:
        mm = indexer_mod.EDGE_REGEX.match(l.strip())
        if (mm and mm.group("predicate") == predicate
                and _norm(mm.group("target")) == tgt
                and _norm(mm.group("source")) == src):
            removed += 1
            continue
        kept.append(l)
    if removed == 0:
        return {"status": "not_found",
                "edge": f"[[{src}]] {predicate} [[{tgt}]]"}
    path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    stats = _run_indexer(force=False, embed=False)
    return {"status": "removed", "removed_count": removed,
            "edges_inserted_after": stats.get("edges_inserted")}


@mcp.tool()
def delete_node(title: str) -> dict:
    """node를 삭제합니다: .md 파일을 지우면 인덱서가 파생 캐시(DB node + 양방향 엣지)를
    재정합하여 정리합니다.

    Markdown이 source of truth이므로 '파일 삭제'가 1차이고 DB는 따라옵니다. 파일을 지운 뒤
    force 재인덱싱이 (a) 파일이 사라진 orphan 노드와 그에 닿는 엣지를 제거하고, (b) 다른
    node가 이 제목을 링크해 생긴 dangling 엣지까지 한 번에 정리합니다. 부분 실패(파일은
    지웠으나 재인덱싱 실패)도 다음 sync가 orphan을 정리하므로 자가 치유됩니다.

    Args:
        title: 삭제할 node 제목
    """
    t = _validate_title(title)
    path = _find_node_path(t)

    # 1) source of truth(파일) 먼저 제거 — 실패하면 DB를 건드리기 전에 에러가 전파(불일치 없음)
    file_removed = False
    if path is not None and path.exists():
        path.unlink()
        file_removed = True

    # 2) 데몬이 orphan 노드 + 그에 닿는 엣지를 정리하고 dangling을 재정합(force reindex).
    stats = _run_indexer(force=True, embed=False)

    warnings = []
    if not file_removed:
        warnings.append("해당 제목의 .md 파일을 찾지 못했습니다(title 불일치 가능). "
                        "DB에 orphan 노드만 있었다면 force reindex가 정리했습니다.")
    return {
        "deleted_title": t,
        "node_removed": file_removed or stats.get("nodes_pruned", 0) > 0,
        "file_removed": file_removed,
        "nodes_pruned": stats.get("nodes_pruned", 0),
        "warnings": warnings,
    }


@mcp.tool()
def reconcile_graph(embed: bool = False) -> dict:
    """전체 엣지를 재구성하여 그동안 쌓인 dangling edge를 일괄 해소합니다.
    (force 엣지 재구성. embed=False면 재임베딩 없이 빠르게 수행)

    write 도구는 기본적으로 증분 인덱싱만 하므로, 새 node가 '기존 node로부터'
    받는 링크는 즉시 연결되지 않습니다. 이 도구(또는 sync_vault(force=True))를
    주기적으로 실행해 그래프를 정합 상태로 맞추세요. 대규모 vault에서도
    재임베딩이 없어 비용이 낮습니다.

    Args:
        embed: True면 누락/변경 임베딩도 함께 보강
    """
    stats = _run_indexer(force=True, embed=embed)
    return {
        "edges_inserted": stats.get("edges_inserted"),
        "edges_rejected": stats.get("edges_rejected"),
        "edges_dangling": stats.get("edges_dangling"),
        "embeddings_built": stats.get("embeddings_built"),
    }


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
