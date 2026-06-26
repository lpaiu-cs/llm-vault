---
id: system_operating_model
title: Second Brain Operating Model
aliases:
  - 운영 모델
  - Operating Model
  - Layer Model
type: System-Specification
moc: "[[Second Brain MOC]]"
parent_moc: "[[Second Brain MOC]]"
tags:
  - System
  - SecondBrain
  - OperatingModel
status: evergreen
created: 2026-06-18
updated: 2026-06-18
version: 1.0
related:
  - "[[Source Policy]]"
  - "[[Ingest Policy]]"
  - "[[Review Policy]]"
  - "[[Naming Convention]]"
---

> [!IMPORTANT] 문서 정체성
> 본 노트는 `ltm-vault`를 **LLM-native second brain**으로 운영하기 위한 최상위
> 멘탈 모델입니다. 각 계층(layer)의 역할과 데이터 흐름을 정의하며, 세부 규칙은
> [[Source Policy]] · [[Ingest Policy]] · [[Review Policy]] · [[Naming Convention]]에
> 위임합니다.

---

## 1. 계층 모델 (Layer Model)

```text
05_Inbox       = 미처리 인입 (unprocessed intake)
06_Raw         = 불변 진실의 원천 (immutable source of truth)
50_Summaries   = 원본 수준 압축 이해 (compressed source-level understanding)
30_Projects    = 활성 작업 대시보드 (active work dashboards)
20_Concepts    = 내구성 개념 지식 (durable conceptual knowledge)
40_Decisions   = 중요 선택과 근거 (important choices and rationale)
60_Questions   = 미해결 연구/구현/행정 질문 (open questions)
70_Conflicts   = 모순과 낡은 가정 (contradictions and stale assumptions)
80_Reviews     = 사람 검증 큐 (human verification queue)
90_Engine      = 런타임·인덱싱·검색·MCP (runtime/index/retrieval/MCP)
```

## 2. 데이터 흐름 (Data Flow)

```text
                  사람 / LLM / 도구 출력
                          │
                          ▼
                   ┌─────────────┐
                   │  05_Inbox   │  미처리 인입
                   └──────┬──────┘
              안정화·증거화 │ (이관, 이후 불변)
                          ▼
                   ┌─────────────┐      참조(source_path)
                   │  06_Raw     │◀──────────────────────┐
                   └──────┬──────┘                       │
                  요약·압축 │                              │
                          ▼                              │
                   ┌──────────────────┐                  │
                   │ 50_Source_Summary│──────────────────┘
                   └──────┬───────────┘
            해석·구조화    │
        ┌─────────────────┼───────────────────────────┐
        ▼                 ▼                ▼            ▼
 ┌────────────┐   ┌────────────┐  ┌────────────┐ ┌────────────┐
 │30_Projects │   │20_Concepts │  │40_Decisions│ │60_Questions│
 │ (대시보드) │   │ (개념 그래프)│  │ (결정 기록)│ │ (열린 질문)│
 └─────┬──────┘   └─────┬──────┘  └─────┬──────┘ └────────────┘
       │                │               │
       └────────────────┼───────────────┘
            품질 게이트   │ (불확실/모순 감지)
            ┌────────────┴────────────┐
            ▼                         ▼
     ┌──────────────┐        ┌──────────────────┐
     │ 70_Conflicts │        │   80_Reviews     │
     │ (모순 보존)  │        │ (사람 검증 큐)   │
     └──────────────┘        └──────────────────┘

  10_MOC: 위 모든 계층을 가로지르는 탐색 지도 (Map of Content)
  90_Engine: 해석 계층을 DuckDB로 컴파일하고 MCP로 검색 제공
```

## 3. 핵심 불변식 (Invariants)

1. **진실의 원천은 `06_Raw/`다.** 해석은 틀릴 수 있으므로, 언제든 원본으로
   되돌아가 검증할 수 있어야 한다. raw는 불변이다.
2. **해석 ≠ 원본.** `20_Concepts/`, `30_Projects/`, `50_Summaries/`는 *해석된 지식*이며,
   가능한 한 `06_Raw/`의 증거를 가리킨다.
3. **틀림을 가정한다.** 불확실(→`80_Reviews/`)과 모순(→`70_Conflicts/`)은
   숨기지 않고 명시적으로 보존한다.
4. **그래프는 안정 지식만.** 9-predicate 엣지([[Ontology Specification]])는
   내구성 있는 관계에만 쓰고, raw/inbox/일시적 연관은 강제로 넣지 않는다.
5. **이 시스템은 개념 관리기가 아니다.** AI 연구 노트, 디버깅 로그, 장기 프로젝트
   결정, 이론 진화, 행정 기록, 스크린샷, 채팅 로그, 개인 워크플로우 기록을 모두
   포괄한다. 개념 페이지는 그중 한 계층일 뿐이다.

## 4. 런타임 (90_Engine)

해석 계층(`10`~`80`)은 `90_Engine/indexer.py`가 DuckDB(`ltm_cache.db`)로 컴파일하고,
`retriever.py`가 BM25 + Dense + graph expansion으로 **계층/신뢰도 인지** 검색을
수행하며, `mcp_server.py`가 MCP 도구로 노출합니다. 세부는 [../SETUP.md](../SETUP.md)
및 [../docs/MCP_TOOLS.md](../docs/MCP_TOOLS.md) 참조.

계층별 인덱싱 정책(per-folder index policy)과 신뢰도 인지 검색은
[[2026-06-18-layer-and-confidence-aware-retrieval]] 결정을 따릅니다:

> - `05_Inbox/` → 인덱싱 제외(휘발성).
> - `06_Raw/` → **전문검색 전용** 인덱싱(검색 가능, 강등). edge 미파싱·그래프 node
>   아님(`graph_node=False`). 원본은 `source_path`로만 참조되고, 요약
>   (`50_Source_Summaries/`)이 그래프상 대리물 역할을 한다.
> - 검색 랭킹은 `계층 × confidence × status` 가중치로 차등. 낮은 신뢰도·폐기 항목은
>   강등+표기. 검토/메타 계층(`60/70/80`)은 기본 검색에서 제외(필요 시 포함 가능).
> - 가중치·필터·주석은 `00_System/Retrieval Policy.yaml`에서 로드됩니다(없으면 내장
>   fallback). 이 값은 **잠정적 사전값(provisional prior)**이며, `90_Engine/eval_retrieval.py`로
>   측정·튜닝합니다(필터 `default_include`와 가중치 `weight`는 분리).

---

## Sources

- 본 운영 모델은 `ltm-vault` 내부 설계 결정에서 도출됨: [[2026-06-18-second-brain-architecture]]
- 관련 개념: [[Hallucination as Default]], [[LLM OS]]
