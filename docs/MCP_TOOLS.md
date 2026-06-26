# MCP Tools

`90_Engine/mcp_server.py` v2.2는 vault를 읽는 도구와 AI가 메모리를 직접 관리하는 write 도구를 함께 제공합니다.

이 문서는 도구 동작과 에이전트 권장 흐름만 다룹니다. 설치와 MCP 클라이언트 설정은 [../SETUP.md](../SETUP.md)를 보세요.

## Read Tools

| 도구 | 역할 |
|---|---|
| `retrieve_knowledge(query, top_k=5, max_hops=2, max_nodes=10, include_raw=True, include_reviews=False, confidence_weighting=True)` | 자연어 쿼리로 관련 지식 node 서브그래프를 검색합니다. BM25, dense embedding, graph expansion 결과를 캡슐 형태로 반환합니다. **계층/신뢰도 인지**로 랭킹합니다(아래 참조). |
| `sync_vault(force=False, embed=True)` | Markdown vault를 DuckDB 캐시로 컴파일합니다. 사람이 파일을 직접 편집한 뒤 호출합니다. |
| `vault_stats()` | node/엣지 수, 임베딩 커버리지, predicate 분포, hub/authority 상위 node를 반환합니다. |
| `review_queue(status="open", layer=None)` | 검토·질문·모순 큐(`60/70/80`)의 항목을 상태별로 모아 반환합니다. 검토 큐 위생용. |

`retrieve_knowledge()`는 단일 소유자 데몬으로 포워딩되어 하이브리드 검색 결과를 반환합니다.

### Layer & Confidence-Aware Retrieval

검색은 계층(layer)·신뢰도(confidence)·상태(status)를 인지합니다
([[2026-06-18-layer-and-confidence-aware-retrieval]]).

- 랭킹 점수 = 하이브리드 점수 × `계층 가중치 × confidence × status`.
  - 검증된 지식(`20_Concepts`/`50_Source_Summaries`)은 높게, `06_Raw`(전문검색 전용)는
    강등, 검토/메타(`60/70/80`)는 더 강등.
  - `confidence: low/medium`, `status: superseded/rejected/stale`는 강등(숨기지 않음).
- 스코프 기본값: `06_Raw`는 포함(강등), 검토/메타 계층은 **제외**.
  - `include_reviews=True` → `60/70/80` 포함.
  - `include_raw=False` → `06_Raw` 제외.
  - `confidence_weighting=False` → confidence 강등 끔.
- 반환 JSON의 `nodes[]`에는 각 node의 `layer/confidence/status/annotation/score`가
  표기되고, XML 캡슐의 `<node>` 태그에도 같은 속성이 붙습니다. `scope` 필드로 적용된
  스코프와 `policy_source`를 확인할 수 있습니다. 에이전트는 이 메타로 출처·불확실성을 판단하세요.

#### 가중치 설정 (config) & 평가

- 가중치/필터/주석은 코드 상수가 아니라 **`00_System/Retrieval Policy.yaml`**에서
  로드됩니다(없으면 retriever 내장 fallback). 우선순위: env `VAULT_RETRIEVAL_POLICY`
  → `00_System/Retrieval Policy.yaml` → `90_Engine/retrieval_policy.yaml` → 내장.
  PyYAML이 있으면 사용하고, 없으면 내장 최소 파서로 읽습니다(선택 의존성).
- **필터(`default_include`)와 랭킹 가중치(`weight`)는 분리**되어 있습니다. 예: `06_Raw`는
  기본 포함+낮은 가중치, `80_Reviews`는 기본 제외+매우 낮은 가중치.
- 이 가중치는 경험적 최적값이 아니라 **잠정적 사전값(provisional prior)**입니다.
  실측 튜닝은 `python3 90_Engine/eval_retrieval.py --db <cache> --queries <set>`로
  MRR@5/Recall@5/`review_leakage_rate`/`raw_overexposure_rate`를 보며 합니다.

## Write Tools

| 도구 | 역할 |
|---|---|
| `list_nodes()` | 전체 node 목록을 반환합니다. edge target으로 써야 할 정확한 제목을 확인할 때 먼저 호출합니다. |
| `create_node(title, body, type="Concept", moc=None, aliases=None, tags=None, edges=None, sources=None, folder="20_Concepts", embed=True, resolve_links=False)` | 새 Markdown node 파일을 만들고 증분 인덱싱합니다. |
| `update_node(title, body=None, edges=None, type=None, moc=None, aliases=None, tags=None, sources=None, embed=True, resolve_links=False)` | 기존 node의 본문, 전체 edge 섹션, 메타데이터를 수정합니다. `node_id`, `id`, `created`는 보존합니다. |
| `upsert_edge(source_title, predicate, target_title, description=None)` | source node에 edge 한 개를 추가합니다. 이미 있으면 중복 추가하지 않습니다. |
| `remove_edge(source_title, predicate, target_title)` | source node에서 지정 edge를 제거합니다. |
| `delete_node(title)` | node 파일과 DB의 해당 node/연결 edge를 삭제합니다. 다른 node의 링크는 dangling이 될 수 있습니다. |
| `reconcile_graph(embed=False)` | 전체 edge를 재구성해 dangling 해소를 시도합니다. 기본값은 재임베딩 없이 빠르게 정합합니다. |

## Edge Rules

edge는 node 본문에 아래 형태로 저장됩니다.

```markdown
- `[[Source Title]] requires [[Target Title]]` — 설명
```

predicate는 9개만 허용됩니다.

`requires` · `utilizes` · `implemented_by` · `extends` · `abstracts` · `causes` · `contradicts` · `replaces` · `defines`

target은 대상 node의 제목, 즉 파일명 stem과 정확히 같아야 합니다. write 전에 `list_nodes()`로 확인하면 dangling edge를 줄일 수 있습니다.

## 그래프 정합 (Reconcile)

write 도구는 기본적으로 증분 인덱싱만 수행합니다. 새 node 자체와 그 node가 내보내는 edge는 바로 반영되지만, **기존 node가 새 node를 향하던 dangling edge**는 전체 edge 재구성 전까지 남을 수 있습니다.

해소 방법(둘 다 데몬의 force reindex로 위임):

- **쓰기 시 즉시 정합** — `create_node(..., resolve_links=True)` / `update_node(..., resolve_links=True)`. 그 node로 향하던 기존 dangling edge를 곧바로 연결합니다.
- **일괄 정합** — `reconcile_graph(embed=False)` 또는 `sync_vault(force=True)`를 주기적으로 호출합니다.

> 과거의 자동 정합 상태머신(`<VAULT_DB>.reconcile.json` + `VAULT_AUTO_RECONCILE`/`VAULT_RECONCILE_DEBOUNCE_SEC`)은 데몬 표준화와 함께 제거됐습니다 — 정합은 이제 위처럼 **명시적으로** 트리거합니다.

## Agent Workflow

메모리를 저장하거나 수정할 때는 아래 순서를 권장합니다.

1. `list_nodes()`로 기존 node 제목과 중복 여부를 확인합니다.
2. 새 개념이면 `create_node()`를 사용합니다.
3. 기존 개념 보강이면 `update_node()`를 사용합니다.
4. 관계 한 개만 추가할 때는 `upsert_edge()`를 사용합니다.
5. 변경 후 중요한 검색을 바로 해야 하면 `reconcile_graph(embed=False)`를 호출합니다.
6. `retrieve_knowledge()`나 `vault_stats()`로 결과를 확인합니다.
7. 주기적으로 `review_queue(status="open")`로 검토·질문·모순 큐를 점검해 비웁니다.

사람이 직접 Markdown 파일을 수정한 경우에는 `sync_vault()`를 호출합니다.
