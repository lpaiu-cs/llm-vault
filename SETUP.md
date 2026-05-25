# Karpathy LLM Framework Vault — Setup Guide

본 Vault를 Cursor / Claude Desktop의 장기 메모리(LTM)로 마운트하기 위한 단계별 설치 가이드.

## 시스템 아키텍처 (한 눈에)

```
┌───────────────────────────────────────────────────────────┐
│  Cursor / Claude Desktop (MCP Client)                     │
│         │                                                 │
│         │ stdio (JSON-RPC over stdin/stdout)              │
│         ▼                                                 │
│  90_Engine/mcp_server.py                                  │
│   ├─ retrieve_knowledge(query, top_k, max_hops)           │
│   ├─ sync_vault(force, embed)                             │
│   └─ vault_stats()                                        │
│         │                                                 │
│         ├──> retriever.py  ──> DuckDB SQL cosine          │
│         │       │           ──> BM25 (in-memory)          │
│         │       │           ──> Ollama (쿼리 임베딩 1회)  │
│         │       │           ──> Adaptive 2-hop graph      │
│         │       │                                         │
│         └──> indexer.py    ──> Markdown 파싱              │
│                 │           ──> Ollama (노트 임베딩 캐시) │
│                 ▼                                         │
│         90_Engine/ltm_cache.db (DuckDB)                   │
│           ├─ nodes (UUID, title, embedding FLOAT[1024])   │
│           └─ edges (9개 술어 CHECK 제약)                  │
│                                                           │
│  ┌──────────────────────────────────────────┐             │
│  │  Ollama (http://localhost:11434)         │             │
│  │  └─ bge-m3 모델 (다국어 SOTA, 2.3GB)     │             │
│  └──────────────────────────────────────────┘             │
└───────────────────────────────────────────────────────────┘
```

---

## 1단계: 의존성 설치

### Python 패키지

```bash
pip install duckdb rank-bm25 mcp
# 선택적 (FastAPI 모드 사용 시):
pip install fastapi "uvicorn[standard]"
```

### Ollama 설치

**macOS / Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:** https://ollama.com/download 에서 설치 파일 다운로드

### 임베딩 모델 다운로드

```bash
ollama pull bge-m3       # 권장: 다국어 SOTA, 1024-dim, 2.3GB
# 또는 가벼운 대안:
# ollama pull nomic-embed-text   # 영어 위주, 768-dim, 270MB
```

### Ollama 서버 확인

```bash
# 대부분의 OS에서 ollama가 백그라운드로 자동 가동됨
ollama serve  # 수동 가동 필요시

# 헬스 체크
curl http://localhost:11434/api/tags
```

---

## 2단계: Vault 디렉터리 구조 정착

본 프로젝트의 27개 마크다운 파일을 권장 구조에 따라 배치:

```
Vault Root/
│
├── 00_System/
│   └── Ontology Specification.md            # 9개 술어 헌법
│
├── 10_MOC/
│   ├── Karpathy LLM Framework MOC.md        # 최상위 MOC
│   ├── Philosophy MOC.md                    # 4대 카테고리 MOC
│   ├── Architecture MOC.md
│   └── Implementation MOC.md
│
├── 20_Concepts/                             # 22개 원자 노드
│   ├── Software 1.0.md
│   ├── Software 2.0.md
│   ├── Software 3.0.md
│   ├── Vibe Coding.md
│   ├── The Bitter Lesson.md
│   ├── Hallucination as Default.md
│   ├── Rule-based AI.md
│   ├── LLM OS.md
│   ├── Transformer.md
│   ├── Context Window.md
│   ├── Tokenizer.md
│   ├── Byte Pair Encoding.md
│   ├── Glitch Tokens.md
│   ├── Tool Use.md
│   ├── Reflection Loop.md
│   ├── minGPT.md
│   ├── nanoGPT.md
│   ├── llm.c.md
│   ├── FlashAttention.md
│   ├── Memory-mapped IO.md
│   └── Gradient Descent.md
│
└── 90_Engine/                               # 머신 전용 (gitignore 권장)
    ├── indexer.py                           # 마크다운 → DuckDB 컴파일러
    ├── retriever.py                         # 2단 하이브리드 검색
    ├── mcp_server.py                        # MCP 서버 (stdio)
    └── ltm_cache.db                         # (자동 생성) DuckDB 캐시
```

`Test Violation Note.md`는 시뮬레이션 산출물이므로 수동 삭제 권장.

---

## 3단계: 초기 인덱싱 (임베딩 컴파일)

```bash
cd <Vault Root>
python3 90_Engine/indexer.py --force --embed --report
```

**예상 출력**:
```
[*] LTM Cache Engine v1.1 → 90_Engine/ltm_cache.db
[*] --force 모드: 모든 파일의 엣지를 강제 재구성
[*] --embed 모드: Ollama bge-m3 @ http://localhost:11434
[*] 발견된 마크다운 파일: 27개
[*] 노드 패스 완료 — 신규: 27, 수정: 0, 무변경: 0
[*] 임베딩 빌드 시작: 27개 노드
  [*] 진행: 5/27
  ...
[*] 임베딩 패스 완료 — 빌드: 27, 실패: 0
[임베딩 커버리지] 27/27 노드 (100%)
[Hub Top 5]
  FlashAttention                           ← 5
  Tool Use                                 ← 4
  ...
```

이후 노트 수정 시:
```bash
# 증분 (변경된 파일만)
python3 90_Engine/indexer.py --embed --report

# 강제 재구성 (술어 가중치 등 헌법 변경 시)
python3 90_Engine/indexer.py --force --embed --report
```

---

## 4단계: MCP 클라이언트 연결

### Cursor (`~/.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "karpathy-vault": {
      "command": "python3",
      "args": ["/absolute/path/to/Vault/90_Engine/mcp_server.py"],
      "env": {
        "VAULT_ROOT": "/absolute/path/to/Vault",
        "VAULT_DB": "/absolute/path/to/Vault/90_Engine/ltm_cache.db",
        "OLLAMA_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "bge-m3"
      }
    }
  }
}
```

### Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS)

동일한 JSON 구조. 경로만 실제 머신에 맞게 수정.

### 연결 확인

Cursor 재시작 후, 채팅에서:
- `@karpathy-vault retrieve_knowledge` 입력 시 자동완성 노출
- 또는 `vault_stats` 호출로 그래프 상태 확인

---

## 5단계: 가동 검증

MCP 클라이언트가 없어도 stdio 직접 호출로 검증 가능:

```bash
# Terminal 1: MCP 서버 가동
VAULT_ROOT=/path/to/vault \
VAULT_DB=/path/to/vault/90_Engine/ltm_cache.db \
python3 90_Engine/mcp_server.py

# Terminal 2: JSON-RPC 직접 송신
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | python3 90_Engine/mcp_server.py
```

---

## 도구 명세

### `retrieve_knowledge(query, top_k=5, max_hops=2, max_nodes=10)`
자연어 쿼리 → 2단 하이브리드 검색 → 캡슐 컨텍스트.

**Returns**:
```json
{
  "mode": "bm25+dense_sql",
  "layer1_meta": {
    "seed_nodes": ["Software 2.0", "..."],
    "activated_edges": ["[[A]] requires [[B]]", "..."],
    "node_scores": {"Software 2.0": 1.0, ...}
  },
  "layer2_xml_capsule": "<retrieved_vault_context>...</retrieved_vault_context>"
}
```

### `sync_vault(force=False, embed=True)`
신규/수정 노트를 DuckDB로 증분 컴파일. 편집 후 즉시 호출 가능.

### `vault_stats()`
현재 그래프 통계 (노드/엣지 수, 임베딩 커버리지, 술어 분포, Hub/Authority Top 5).

---

## 9개 술어 헌법 (요약)

DuckDB CHECK 제약으로 강제됨. 노트에 다른 술어 사용 시 인덱싱 단계에서 `[REJECT]` 로그 출력 후 거부.

| Predicate | 분기 질문 |
|-----------|-----------|
| `requires` | B 없으면 A 존재 불가능 |
| `utilizes` | A가 B를 도구로 쓰지만 B 없이도 A 존재 가능 |
| `implemented_by` | 추상 명세 A가 구체 B로 실현 |
| `extends` | A가 B와 같은 층위에서 기능 추가 |
| `abstracts` | A가 B를 한 층 위에서 복잡도 감춤 |
| `causes` | A의 발생이 B를 유발 |
| `contradicts` | A와 B 양립 불가 |
| `replaces` | A가 기존 B를 기능적으로 대체 |
| `defines` | A가 B의 공식 정의 출처 (문서·강의·에세이) |

전체 상세 명세는 `00_System/Ontology Specification.md` 참조.

---

## Troubleshooting

### `[REJECT] 화이트리스트 외 술어`
헌법 9개 외 술어 사용. §4 Fallback Rule로 9개 안에 매핑하거나 엣지 선언 회피.

### `Dangling edge`
링크된 노트가 아직 미생성. 해당 노트 생성 후 `--force` 재인덱싱하면 자동 활성화.

### `Ollama 응답 실패 (BM25-only로 fallback)`
Ollama 서버 미가동 또는 모델 미설치. 인덱서는 graceful skip하고 BM25-only 모드로 가동.

### MCP 서버 spawn 실패
- Python 경로가 절대 경로인지 확인
- VAULT_DB 파일 존재 여부 확인 (먼저 indexer 실행 필수)
- mcp 패키지 설치 확인: `pip show mcp`

---

## 파일 목록

| 파일 | 역할 |
|------|------|
| `indexer.py` | 마크다운 → DuckDB 컴파일러 (+ Ollama 임베딩) |
| `retriever.py` | 2단 하이브리드 검색 런타임 (CLI + FastAPI) |
| `mcp_server.py` | MCP stdio 서버 (Cursor/Claude Desktop 통합) |
| `mock_ollama.py` | 테스트용 Mock Ollama (실 가동 시 폐기) |
| `Ontology Specification.md` | 9개 술어 헌법 |
| `Karpathy LLM Framework MOC.md` | 최상위 MOC |
| 4 Category MOCs + 22 atomic notes | 지식 코퍼스 |

Vault 통계 (현재 상태):
- 27 노드 (Concept 22 + MOC 4 + System 1)
- 45 엣지 (인덱서 v1.1 기준 적재)
- 8/9 술어 활성화 (`defines`만 표 형식에 있어 미활성)
- 100% 임베딩 커버리지 (bge-m3, 1024-dim)
