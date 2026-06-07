# llm-vault

> Markdown/Obsidian vault를 DuckDB + Ollama + MCP로 컴파일해 AI 에이전트가 검색 가능한 장기 메모리(LTM)로 쓰게 만드는 오픈소스 템플릿.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)

## 이게 뭔가요?

`llm-vault`는 두 가지를 함께 제공합니다.

1. **Obsidian Vault**: Markdown 노트를 지식 그래프로 관리하는 개인 지식 베이스
2. **AI memory runtime**: Antigravity, Cursor, Claude Desktop 같은 MCP 클라이언트가 vault를 검색하고 관리할 수 있게 하는 Python MCP 서버

기본 노트는 Karpathy의 LLM 멘탈 모델을 예시 코퍼스로 제공합니다. 그대로 읽어도 되고, private repo로 복제해 자기만의 연구 메모리로 확장해도 됩니다.

에이전트가 질문을 받으면 vault에서 관련 노트를 검색해 컨텍스트로 사용할 수 있습니다. v2.2 MCP 서버는 검색뿐 아니라 노트 생성, 수정, 엣지 관리, 그래프 정합까지 지원합니다.

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
├── SETUP.md
├── docs/
│   ├── ANTIGRAVITY.md
│   └── MCP_TOOLS.md
├── 00_System/
│   └── Ontology Specification.md
├── 10_MOC/
│   ├── Karpathy LLM Framework MOC.md
│   ├── Philosophy MOC.md
│   ├── Architecture MOC.md
│   └── Implementation MOC.md
├── 20_Concepts/
│   └── ...
└── 90_Engine/
    ├── indexer.py
    ├── retriever.py
    ├── mcp_server.py
    ├── mock_ollama.py
    └── ltm_cache.db
```

숫자 접두사는 Obsidian의 자연 정렬과 읽기 순서를 위한 것입니다. 핵심 규칙은 `00_System/Ontology Specification.md`의 9개 술어 헌법입니다.

## 일상 워크플로우

노트는 사람이 직접 Markdown으로 작성해도 되고, MCP write 도구로 만들 수도 있습니다.

- 사람이 편집한 뒤에는 `sync_vault()` 또는 인덱서 실행으로 캐시를 갱신합니다.
- 에이전트가 메모리를 저장할 때는 `list_notes()`로 기존 제목을 확인한 뒤 `create_note()`, `update_note()`, `upsert_edge()`를 사용합니다.
- dangling edge가 생기면 자동 정합이 처리하거나 `reconcile_graph()`로 즉시 정리합니다.

노트 작성 시 edge predicate는 아래 9개만 허용됩니다.

`requires` · `utilizes` · `implemented_by` · `extends` · `abstracts` · `causes` · `contradicts` · `replaces` · `defines`

## 더 알아보기

- 온톨로지 헌법: [00_System/Ontology Specification.md](00_System/Ontology%20Specification.md)
- 시스템 멘탈 모델: [10_MOC/Karpathy LLM Framework MOC.md](10_MOC/Karpathy%20LLM%20Framework%20MOC.md)
- 설치와 운영: [SETUP.md](SETUP.md)
- MCP 도구: [docs/MCP_TOOLS.md](docs/MCP_TOOLS.md)

## 라이선스

MIT License. 자세한 내용은 [LICENSE](LICENSE)를 참조하세요.

## 출처

- [Andrej Karpathy](https://karpathy.ai)
- [Intro to Large Language Models](https://www.youtube.com/watch?v=zjkBMFhNj_g)
- [Let's build the GPT Tokenizer](https://www.youtube.com/watch?v=zduSFxRajkE)
- [Software 2.0 Essay](https://karpathy.medium.com/software-2-0-a64152b37c35)
- [llm.c GitHub](https://github.com/karpathy/llm.c)
- [nanoGPT GitHub](https://github.com/karpathy/nanoGPT)
