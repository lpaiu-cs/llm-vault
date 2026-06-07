# MCP Tools

`90_Engine/mcp_server.py` v2.2는 vault를 읽는 도구와 AI가 메모리를 직접 관리하는 write 도구를 함께 제공합니다.

이 문서는 도구 동작과 에이전트 권장 흐름만 다룹니다. 설치와 MCP 클라이언트 설정은 [../SETUP.md](../SETUP.md)를 보세요.

## Read Tools

| 도구 | 역할 |
|---|---|
| `retrieve_knowledge(query, top_k=5, max_hops=2, max_nodes=10)` | 자연어 쿼리로 관련 지식 서브그래프를 검색합니다. BM25, dense embedding, graph expansion 결과를 캡슐 형태로 반환합니다. |
| `sync_vault(force=False, embed=True)` | Markdown vault를 DuckDB 캐시로 컴파일합니다. 사람이 파일을 직접 편집한 뒤 호출합니다. |
| `vault_stats()` | 노드/엣지 수, 임베딩 커버리지, predicate 분포, hub/authority 상위 노드를 반환합니다. |

`retrieve_knowledge()`는 자동 정합 조건이 맞으면 pending 변경분을 한 번 정리한 뒤 검색합니다.

## Write Tools

| 도구 | 역할 |
|---|---|
| `list_notes()` | 전체 노트 목록을 반환합니다. edge target으로 써야 할 정확한 제목을 확인할 때 먼저 호출합니다. |
| `create_note(title, body, type="Concept", moc=None, aliases=None, tags=None, edges=None, sources=None, folder="20_Concepts", embed=True, resolve_links=False)` | 새 Markdown 노트를 만들고 증분 인덱싱합니다. |
| `update_note(title, body=None, edges=None, type=None, moc=None, aliases=None, tags=None, sources=None, embed=True, resolve_links=False)` | 기존 노트의 본문, 전체 edge 섹션, 메타데이터를 수정합니다. `node_id`, `id`, `created`는 보존합니다. |
| `upsert_edge(source_title, predicate, target_title, description=None)` | source 노트에 edge 한 개를 추가합니다. 이미 있으면 중복 추가하지 않습니다. |
| `remove_edge(source_title, predicate, target_title)` | source 노트에서 지정 edge를 제거합니다. |
| `delete_node(title)` | 노트 파일과 DB의 해당 노드/연결 edge를 삭제합니다. 다른 노트의 링크는 dangling이 될 수 있습니다. |
| `reconcile_graph(embed=False)` | 전체 edge를 재구성해 dangling 해소를 시도합니다. 기본값은 재임베딩 없이 빠르게 정합합니다. |

## Edge Rules

edge는 노트 본문에 아래 형태로 저장됩니다.

```markdown
- `[[Source Title]] requires [[Target Title]]` — 설명
```

predicate는 9개만 허용됩니다.

`requires` · `utilizes` · `implemented_by` · `extends` · `abstracts` · `causes` · `contradicts` · `replaces` · `defines`

target은 대상 노트의 제목, 즉 파일명 stem과 정확히 같아야 합니다. write 전에 `list_notes()`로 확인하면 dangling edge를 줄일 수 있습니다.

## Auto Reconcile

write 도구는 기본적으로 증분 인덱싱만 수행합니다. 새 노트 자체와 그 노트가 내보내는 edge는 바로 반영되지만, 기존 노트가 새 노트를 향하던 dangling edge는 전체 edge 재구성 전까지 남을 수 있습니다.

v2.2는 이 비용을 줄이기 위해 자동 정합 상태를 `<VAULT_DB>.reconcile.json`에 저장합니다.

- write 도구 호출 시 pending 상태를 기록합니다.
- `retrieve_knowledge()` 호출 시 pending이 있고 debounce 시간이 지났으면 `force=True, embed=False` 정합을 1회 수행합니다.
- 기본 debounce는 600초입니다.

환경 변수:

| 변수 | 기본값 | 설명 |
|---|---:|---|
| `VAULT_AUTO_RECONCILE` | `1` | `0`, `false`, `no`로 설정하면 자동 정합을 끕니다. |
| `VAULT_RECONCILE_DEBOUNCE_SEC` | `600` | 자동 정합 최소 간격입니다. |

즉시 정합이 필요하면 `reconcile_graph(embed=False)`를 호출하거나 `create_note(..., resolve_links=True)`, `update_note(..., resolve_links=True)`를 사용합니다.

## Agent Workflow

메모리를 저장하거나 수정할 때는 아래 순서를 권장합니다.

1. `list_notes()`로 기존 제목과 중복 여부를 확인합니다.
2. 새 개념이면 `create_note()`를 사용합니다.
3. 기존 개념 보강이면 `update_note()`를 사용합니다.
4. 관계 한 개만 추가할 때는 `upsert_edge()`를 사용합니다.
5. 변경 후 중요한 검색을 바로 해야 하면 `reconcile_graph(embed=False)`를 호출합니다.
6. `retrieve_knowledge()`나 `vault_stats()`로 결과를 확인합니다.

사람이 직접 Markdown 파일을 수정한 경우에는 `sync_vault()`를 호출합니다.
