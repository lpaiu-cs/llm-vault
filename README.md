# Karpathy LLM Framework Vault

> Andrej Karpathy의 LLM 사상을 Obsidian 지식 그래프 + DuckDB + Ollama로 컴파일한 **AI 에이전트용 장기 메모리(LTM)** 시스템.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)

---

## 이게 뭔가요?

본 레포지토리는 **두 가지 정체성**을 동시에 가집니다:

1. **Obsidian Vault** — Karpathy의 LLM 멘탈 모델 27개 노트가 지식 그래프로 연결된 개인 지식 베이스
2. **에이전트 LTM 엔진** — 그 Vault를 Cursor/Claude Desktop 같은 AI 에이전트가 **장기 메모리로 마운트**할 수 있게 만드는 Python 런타임

질문하면 의미적으로 가장 가까운 노트들이 자동으로 컨텍스트에 주입됩니다:

```
나: "Vibe Coding을 실전에 쓰려면 무슨 위험을 알아야 해?"

에이전트 (LTM 자동 조회 후):
"너의 Vault에 따르면, Vibe Coding은 Software 3.0을 전제로 하고
 Reflection Loop가 필수야 — 왜냐하면 Hallucination이 LLM의
 디폴트라서 코드를 직접 읽지 않으면 환각이 누적되거든..."
```

---

## 5분 빠른 시작

### 사전 요구사항

- **Python 3.9+**
- **Obsidian** (옵션, 노트 편집·시각화용)
- **Ollama** (의미 검색 활성화 필수, 없으면 BM25-only 가동)

### 설치

```bash
# 1. 레포 클론
git clone https://github.com/<your-username>/karpathy-llm-vault.git
cd karpathy-llm-vault

# 2. Python 의존성
pip install -r requirements.txt

# 3. Ollama 설치 (https://ollama.com/download)
#    macOS/Linux:
curl -fsSL https://ollama.com/install.sh | sh
#    Windows: 설치 파일 다운로드

# 4. 임베딩 모델 다운로드 (다국어 SOTA, ~2.3GB)
ollama pull bge-m3

# 5. 초기 인덱싱 (마크다운 → DuckDB 컴파일)
python3 90_Engine/indexer.py --force --embed --report
```

성공하면 `[임베딩 커버리지] 27/27 노드 (100%)` 출력. 끝.

### Obsidian으로 열기

1. Obsidian 실행
2. `Open folder as vault` → 이 레포 폴더 선택
3. 첫 노트: `10_MOC/Karpathy LLM Framework MOC.md` 열어서 그래프 탐색 시작

### Cursor / Claude Desktop 연결 (선택)

설정 파일에 다음 추가:

**Cursor** (`~/.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "karpathy-vault": {
      "command": "python3",
      "args": ["/절대경로/karpathy-llm-vault/90_Engine/mcp_server.py"],
      "env": {
        "VAULT_ROOT": "/절대경로/karpathy-llm-vault",
        "VAULT_DB": "/절대경로/karpathy-llm-vault/90_Engine/ltm_cache.db",
        "OLLAMA_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "bge-m3"
      }
    }
  }
}
```

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):
동일한 JSON 구조.

재시작하면 채팅에서 `@karpathy-vault` 도구가 자동 등장.

---

## 폴더 구조

```
karpathy-llm-vault/
│
├── README.md                  # 이 파일
├── SETUP.md                   # 상세 설치 가이드
├── LICENSE                    # MIT
├── requirements.txt           # Python 의존성
├── .gitignore                 # DuckDB 캐시 등 제외
│
├── 00_System/                 # 시스템 헌법
│   └── Ontology Specification.md   # 9개 술어 정의·규칙
│
├── 10_MOC/                    # Map of Content (4개 카테고리 + 1 루트)
│   ├── Karpathy LLM Framework MOC.md   ← 시작점
│   ├── Philosophy MOC.md
│   ├── Architecture MOC.md
│   └── Implementation MOC.md
│
├── 20_Concepts/               # 원자 지식 노드 (22개)
│   ├── Software 2.0.md
│   ├── Software 3.0.md
│   ├── Vibe Coding.md
│   ├── The Bitter Lesson.md
│   ├── LLM OS.md
│   ├── Transformer.md
│   ├── Byte Pair Encoding.md
│   ├── nanoGPT.md
│   ├── llm.c.md
│   └── ... (총 22개)
│
└── 90_Engine/                 # LTM 머신 (Obsidian이 자동 무시)
    ├── indexer.py             # 마크다운 → DuckDB 컴파일러
    ├── retriever.py           # 2단 하이브리드 검색
    ├── mcp_server.py          # MCP stdio 서버 (Cursor/Claude 연동)
    ├── mock_ollama.py         # 개발/테스트용 (실 가동 시 불필요)
    └── ltm_cache.db           # (자동 생성, gitignore됨)
```

**왜 폴더에 숫자 접두사?** Obsidian의 파일 목록 자연 정렬 + 의도된 우선순위(System → MOC → Concept → Engine) 표시. 4대원칙 §1 "명사형 단일 엔티티"는 *파일명*에만 적용되고 폴더는 자유.

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│  사용자 (Obsidian 편집 OR Cursor/Claude 채팅)            │
│         │                                               │
│         ├─ Obsidian: 노트 직접 편집·시각화              │
│         └─ MCP Client: 자연어 질문 → 도구 호출          │
│                  │                                      │
│                  ▼                                      │
│         90_Engine/mcp_server.py (stdio JSON-RPC)        │
│           ├─ retrieve_knowledge(query)                  │
│           ├─ sync_vault()                               │
│           └─ vault_stats()                              │
│                  │                                      │
│                  ├──> retriever.py                      │
│                  │     ├─ BM25 + Ollama Dense + RRF     │
│                  │     ├─ DuckDB SQL cosine similarity  │
│                  │     └─ Adaptive 2-hop graph 확장     │
│                  │                                      │
│                  └──> indexer.py (sync_vault 시)        │
│                        ├─ MD5 증분 변경 감지            │
│                        ├─ Ollama 임베딩 캐싱            │
│                        └─ 9 술어 CHECK 제약 강제        │
│                                                         │
│  ┌──────────────────────────────────────────┐           │
│  │  DuckDB ltm_cache.db                     │           │
│  │   ├─ nodes (UUID, title, embedding[])    │           │
│  │   └─ edges (9 술어 화이트리스트)         │           │
│  └──────────────────────────────────────────┘           │
│                                                         │
│  ┌──────────────────────────────────────────┐           │
│  │  Ollama @ localhost:11434                │           │
│  │   └─ bge-m3 (다국어 1024-dim)            │           │
│  └──────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

---

## 일상 워크플로우

### 새 노트 추가

`20_Concepts/내_새_개념.md` 파일을 만들고 다음 템플릿 사용:

```markdown
---
id: concept_my_new_idea
title: 내 새 개념
aliases:
  - 별칭1
type: Concept
moc: "[[Philosophy MOC]]"          # 또는 다른 MOC
parent_moc: "[[Philosophy MOC]]"
tags:
  - 카테고리
status: draft
created: 2026-XX-XX
version: 1.0
node_id: <UUID 생성기로 생성>
---

# 내 새 개념

3문장 정도의 정의.

## 핵심 메커니즘

1. ...
2. ...

## 핵심 엣지

- `[[내 새 개념]] requires [[기존 노트]]` — 이유 설명
- `[[기존 노트2]] causes [[내 새 개념]]` — 인과 관계 설명

## Sources

- [출처](https://...)
```

### 노트 작성 시 9 술어만 사용

`requires` · `utilizes` · `implemented_by` · `extends` · `abstracts` · `causes` · `contradicts` · `replaces` · `defines`

다른 술어 사용 시 인덱서가 `[REJECT]` 로그 출력 후 거부. 상세 규칙은 `00_System/Ontology Specification.md` 참조.

### 노트 수정 후 재인덱싱

```bash
# 증분 (변경된 파일만)
python3 90_Engine/indexer.py --embed --report

# 강제 재구성 (Dangling edges 해소 시)
python3 90_Engine/indexer.py --force --embed --report
```

또는 MCP 클라이언트에서 `sync_vault()` 호출.

### 검색 테스트 (CLI)

```bash
python3 90_Engine/retriever.py \
    --query "환각 검증 메커니즘은?" \
    --top-k 5 --hops 2
```

### Obsidian Graph 뷰 설정 권장

`Settings → Files & Links` 에서:
- `Excluded files` → `90_Engine/` 추가 (그래프에서 코드 폴더 숨김)
- `New note location` → `Specified folder` → `20_Concepts` (기본 생성 위치)

---

## 핵심 개념 빠른 참조

| 개념 | 한 줄 정의 |
|------|-----------|
| `[[Software 2.0]]` | 코드를 인간이 쓰는 대신 데이터·손실함수로 신경망 훈련하여 프로그램 자동 탐색 |
| `[[Software 3.0]]` | 자연어 프롬프트·툴 라우팅·에이전트 루프로 소프트웨어 가동 (LLM 중심) |
| `[[Vibe Coding]]` | 자연어 의도만 제시하고 AI가 코드 구현·실행 (2025 Karpathy) |
| `[[LLM OS]]` | LLM = CPU, Context Window = RAM, Tool Use = 주변기기 |
| `[[The Bitter Lesson]]` | 인간 휴리스틱은 장기적으로 컴퓨테이션 스케일링에 패배 (Sutton) |
| `[[Hallucination as Default]]` | LLM은 환각이 디폴트, 사실은 통제된 운 좋은 환각일 뿐 |
| `[[Byte Pair Encoding]]` | 통계 빈도 기반 서브워드 토큰화 (GPT 표준) |
| `[[Glitch Tokens]]` | 학습 데이터 비대칭으로 발생하는 추론 붕괴 토큰 |

---

## 트러블슈팅

### `ollama: command not found`
Ollama가 설치되지 않음. https://ollama.com/download 에서 설치.

### `pull model failed: bge-m3`
인터넷 연결 확인. 대안 (가벼움): `ollama pull nomic-embed-text` (영어 위주, 270MB)

### 인덱싱 시 `Ollama 응답 실패`
Ollama 서버가 가동되지 않음. 대부분의 OS에서 자동 가동되지만 수동 가동 필요시:
```bash
ollama serve
```

### `[REJECT] 화이트리스트 외 술어 'enables'`
9 술어 외 단어 사용. `00_System/Ontology Specification.md` §4 Fallback Rule로 9개에 매핑.

### Cursor/Claude Desktop에서 도구가 안 보임
1. MCP 설정 JSON의 경로가 **절대 경로**인지 확인
2. `VAULT_DB` 파일 존재 여부 확인 (없으면 indexer 먼저 실행)
3. 클라이언트 완전 종료 후 재시작
4. 로그 확인: Claude Desktop은 `~/Library/Logs/Claude/mcp-server-karpathy-vault.log`

### Dangling edges가 많다고 나옴
해당 링크 대상 노트가 아직 미생성. 자연스러운 백로그 — 그 노트를 만들면 자동 해소.

---

## 확장 아이디어

- **Pedagogy MOC + 3개 노트** (Eureka Labs / Intro to LLMs / Teacher and AI Model) — 4번째 축 완성
- **Reflection 검증 루프** — 에이전트 답변의 엔티티를 그래프 역조회하여 환각 차단
- **나만의 도메인 추가** — Karpathy 노트 옆에 본인 분야 노트를 같은 9 술어 헌법으로 작성하면 그래프가 자연스럽게 연결됨
- **HNSW 벡터 인덱스** — 노트 2,000개 넘으면 DuckDB VSS extension 도입

---

## 본 프로젝트의 자기참조적 우아함

이 시스템은 자신이 다루는 사상을 자기 자신으로 구현했습니다:

- **Software 2.0 정신** = 인덱서가 인간 규칙(`if-else`)이 아닌 헌법 위의 데이터로 그래프를 컴파일
- **llm.c 정신** = sentence-transformers·PyTorch 배제, urllib + DuckDB만으로 가동
- **Hallucination as Default 대응** = 9 술어 CHECK 제약이 DB 레벨에서 환각 차단
- **Vibe Coding** = 자연어 의도 → AI 구현 → 인간 검토 → 보정 → 배포 루프 자체로 빌드됨

---

## 라이선스

MIT License. 자유롭게 fork·수정·확장. 상세는 [LICENSE](LICENSE) 참조.

## 기여

이슈와 PR 환영. 새 노트 추가 시 9 술어 헌법 준수 필수 (인덱서가 자동 검증).

---

## 더 알아보기

- 상세 설치 가이드: [SETUP.md](SETUP.md)
- 온톨로지 헌법: [00_System/Ontology Specification.md](00_System/Ontology%20Specification.md)
- 시스템 멘탈 모델: [10_MOC/Karpathy LLM Framework MOC.md](10_MOC/Karpathy%20LLM%20Framework%20MOC.md)

## 출처

- [Andrej Karpathy](https://karpathy.ai)
- [Intro to Large Language Models](https://www.youtube.com/watch?v=zjkBMFhNj_g)
- [Let's build the GPT Tokenizer](https://www.youtube.com/watch?v=zduSFxRajkE)
- [Software 2.0 Essay](https://karpathy.medium.com/software-2-0-a64152b37c35)
- [llm.c GitHub](https://github.com/karpathy/llm.c)
- [nanoGPT GitHub](https://github.com/karpathy/nanoGPT)
