# llm-vault

> Obsidian 호환 Markdown vault에 **출처 기반 아카이브 규율 + 결정 기록 + 모순 추적**을
> 더하고, DuckDB + Ollama + MCP 기반 메모리 런타임으로 컴파일한 **LLM-native second brain**.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)

> **📦 이 저장소는 "프레임워크 템플릿"입니다.** 엔진(`90_Engine/`) + 정책(`00_System/`) +
> 문서/스크립트 + **빈 vault 스켈레톤**(지식 계층은 `README`만) + 동작을 보여주는
> [`examples/mini-vault/`](examples/mini-vault/)로 구성됩니다. **실제 지식은 담겨 있지
> 않습니다.** 자신의 second brain으로 쓰려면 이 템플릿을 복제해 **개인 private 인스턴스**를
> 만들고, 실제 지식은 거기에만 쌓으세요. 경계·운영법은 [SETUP.md](SETUP.md) §8 참조.

## 이게 뭔가요?

`llm-vault`는 Obsidian 호환 Markdown vault, 출처 기반(source-grounded) 아카이브 규율,
결정 기록(decision records), 모순 추적(contradiction tracking), 그리고 MCP 기반
메모리 런타임을 결합한 **LLM-native second brain**입니다.

핵심 전제는 **"LLM은 틀릴 수 있다"**([[Hallucination as Default]])입니다. 그래서 이
시스템에서 원본(raw source), 출처 인용, 불확실성 표시, 모순 보존, 사람 검토 큐는
선택이 아니라 필수입니다. 단순한 개념 그래프가 아니라, AI 연구 노트·디버깅 로그·장기
프로젝트 결정·이론 진화·행정 기록·스크린샷·채팅 로그·개인 워크플로우 기록을 모두
포괄합니다.

에이전트(Claude, Cursor, Antigravity 등)는 작업 전 [AGENTS.md](AGENTS.md)를 먼저 읽고,
전체 멘탈 모델은 [00_System/Second Brain Operating Model.md](00_System/Second%20Brain%20Operating%20Model.md)를 따릅니다.

## 6개 계층 (Layers)

| 계층 | 경로 | 역할 |
|------|------|------|
| **아카이브 (Archive)** | `05_Inbox/`, `06_Raw/` | 미처리 인입(05_Inbox, 인덱싱 제외) → 불변 원본(06_Raw, 전문검색 전용·그래프 제외). |
| **위키/지식 (Wiki/Knowledge)** | `20_Concepts/`, `50_Source_Summaries/`, `10_MOC/` | 원본 요약과 내구성 개념 지식, 탐색 지도. |
| **프로젝트 (Project)** | `30_Projects/` | 활성 작업 대시보드. |
| **결정 (Decision)** | `40_Decisions/` | 중요 선택과 근거. 기존 결정은 불변(supersede 방식). |
| **검토 (Review)** | `60_Open_Questions/`, `70_Contradictions/`, `80_Reviews/` | 열린 질문, 모순 보존, 사람 검증 큐. |
| **런타임 (Runtime)** | `90_Engine/` | DuckDB 인덱싱, 하이브리드 검색, MCP 서버. |

데이터 흐름: `05_Inbox/` → `06_Raw/`(불변) → `50_Source_Summaries/` → 해석 계층 갱신 →
검토/모순/질문 라우팅 → `90_Engine/` 재인덱싱. 자세한 그림은
[Second Brain Operating Model](00_System/Second%20Brain%20Operating%20Model.md) 참조.

## 시작하기

- 설치, 초기 인덱싱, MCP 클라이언트 연결: [SETUP.md](SETUP.md)
- MCP 도구 명세와 AI memory write 흐름: [docs/MCP_TOOLS.md](docs/MCP_TOOLS.md)
- Antigravity 전용 연결 가이드: [docs/ANTIGRAVITY.md](docs/ANTIGRAVITY.md)

최소 흐름은 다음과 같습니다.

1. Python 의존성 설치
2. Ollama와 `bge-m3` 모델 준비
3. `90_Engine/indexer.py`로 Markdown을 DuckDB 캐시로 컴파일
4. MCP 클라이언트 설정에 `90_Engine/mcp_server.py` 등록

자세한 명령과 OS별 설정 예시는 [SETUP.md](SETUP.md)를 기준으로 보세요.

## 폴더 구조

```text
llm-vault/
├── README.md
├── AGENTS.md                  # LLM 에이전트 운영 지침
├── SETUP.md
├── docs/
│   ├── ANTIGRAVITY.md
│   └── MCP_TOOLS.md
├── 00_System/                 # 온톨로지 + second brain 정책
│   ├── Ontology Specification.md
│   ├── Second Brain Operating Model.md
│   ├── Source Policy.md
│   ├── Ingest Policy.md
│   ├── Review Policy.md
│   └── Naming Convention.md
├── 05_Inbox/                  # 미처리 인입 (인덱싱 제외)
├── 06_Raw/                    # 불변 원본 = 진실의 원천 (전문검색 전용, 그래프 제외)
├── 10_MOC/                    # 탐색 지도 (Map of Content)
├── 20_Concepts/               # 내구성 개념 지식
├── 30_Projects/               # 활성 작업 대시보드
├── 40_Decisions/              # 결정 기록
├── 50_Source_Summaries/       # 원본 압축 이해
├── 60_Open_Questions/         # 미해결 질문
├── 70_Contradictions/         # 모순·낡은 가정 보존
├── 80_Reviews/                # 사람 검증 큐
└── 90_Engine/                 # 런타임/인덱스/MCP
    ├── indexer.py
    ├── retriever.py
    ├── mcp_server.py
    └── ltm_cache.db           # local generated cache, ignored by git
```

숫자 접두사는 Obsidian의 자연 정렬과 읽기 순서를 위한 것입니다. 핵심 규칙은
`00_System/Ontology Specification.md`의 9개 술어 헌법과 `00_System/`의 second brain
정책 문서들입니다.

## 일상 워크플로우

node는 사람이 직접 Markdown으로 작성해도 되고, MCP write 도구로 만들 수도 있습니다.
인입(ingest)의 표준 절차는 [Ingest Policy](00_System/Ingest%20Policy.md)를 따릅니다.

- 사람이 편집한 뒤에는 `sync_vault()` 또는 인덱서 실행으로 캐시를 갱신합니다.
- 에이전트가 메모리를 저장할 때는 `list_notes()`로 기존 제목을 확인한 뒤
  `create_note()`, `update_note()`, `upsert_edge()`를 사용합니다.
- dangling edge가 생기면 자동 정합이 처리하거나 `reconcile_graph()`로 즉시 정리합니다.
- **모든 source를 concept node로 만들지 않습니다.** 기본 도착지는
  `50_Source_Summaries/`이며, 내구성 지식만 `20_Concepts/`로 승격합니다.
- 검색은 **계층/신뢰도 인지**입니다. `06_Raw/`는 전문검색 전용으로 검색되되 강등되고,
  낮은 신뢰도·폐기 항목도 강등+표기되며, 검토 계층(`60/70/80`)은 기본 검색에서 빠집니다
  (`retrieve_knowledge(..., include_reviews=true)`로 포함). 검토 큐 점검은
  `review_queue()`로. 근거: [[2026-06-18-layer-and-confidence-aware-retrieval]].

node 작성 시 edge predicate는 아래 9개만 허용됩니다(안정적 지식 관계에만 사용).

`requires` · `utilizes` · `implemented_by` · `extends` · `abstracts` · `causes` · `contradicts` · `replaces` · `defines`

## 더 알아보기

- 에이전트 지침: [AGENTS.md](AGENTS.md)
- 운영 모델: [00_System/Second Brain Operating Model.md](00_System/Second%20Brain%20Operating%20Model.md)
- 정책: [Source Policy](00_System/Source%20Policy.md) · [Ingest Policy](00_System/Ingest%20Policy.md) · [Review Policy](00_System/Review%20Policy.md) · [Naming Convention](00_System/Naming%20Convention.md)
- 온톨로지 헌법: [00_System/Ontology Specification.md](00_System/Ontology%20Specification.md)
- 초기 코퍼스(LLM 멘탈 모델): [10_MOC/Karpathy LLM Framework MOC.md](10_MOC/Karpathy%20LLM%20Framework%20MOC.md)
- 설치와 운영: [SETUP.md](SETUP.md) · MCP 도구: [docs/MCP_TOOLS.md](docs/MCP_TOOLS.md)

## 라이선스

MIT License. 자세한 내용은 [LICENSE](LICENSE)를 참조하세요.

## 출처

- [Andrej Karpathy](https://karpathy.ai)
- [Intro to Large Language Models](https://www.youtube.com/watch?v=zjkBMFhNj_g)
- [Let's build the GPT Tokenizer](https://www.youtube.com/watch?v=zduSFxRajkE)
- [Software 2.0 Essay](https://karpathy.medium.com/software-2-0-a64152b37c35)
- [llm.c GitHub](https://github.com/karpathy/llm.c)
- [nanoGPT GitHub](https://github.com/karpathy/nanoGPT)
