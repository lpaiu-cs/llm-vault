# llm-vault Setup Guide

이 문서는 `llm-vault`를 로컬에서 인덱싱하고 Antigravity / Cursor / Claude Desktop 같은 MCP 클라이언트의 장기 메모리(LTM)로 연결하는 설치 기준 문서입니다.

MCP 도구의 상세 스펙은 반복하지 않고 [docs/MCP_TOOLS.md](docs/MCP_TOOLS.md)에 둡니다.

## 아키텍처

```text
Antigravity / Cursor / Claude Desktop
        │
        │ stdio MCP
        ▼
90_Engine/mcp_server.py
        ├─ read tools: retrieve_knowledge, sync_vault, vault_stats
        ├─ write tools: list_notes, create_note, update_note, edge CRUD, reconcile_graph
        │
        ├── retriever.py
        │     ├─ BM25
        │     ├─ DuckDB SQL cosine
        │     ├─ Ollama query embedding
        │     └─ adaptive graph expansion
        │
        └── indexer.py
              ├─ Markdown parsing
              ├─ 9-predicate validation
              ├─ UUID / metadata preservation
              └─ Ollama node embedding cache

90_Engine/ltm_cache.db
        ├─ nodes
        └─ edges
```

## 1. 의존성 설치

Python 3.9+가 필요합니다. 레포 루트에서 실행합니다.

```bash
pip install -r requirements.txt
```

`requirements.txt`에는 MCP 서버와 선택적 FastAPI retriever 모드에 필요한 Python 패키지가 포함되어 있습니다.

## 2. Ollama 준비

Ollama는 Python 패키지가 아니라 별도 시스템 프로그램입니다.

macOS / Linux:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Windows:

```text
https://ollama.com/download
```

임베딩 모델:

```bash
ollama pull bge-m3
```

서버 확인:

```bash
ollama list
curl http://localhost:11434/api/tags
```

의미 검색을 쓰지 못하는 환경에서는 Ollama 오류가 나도 BM25-only 모드로 일부 기능이 동작합니다.

## 3. 초기 인덱싱

Markdown vault를 DuckDB 캐시로 컴파일합니다.

```bash
python3 90_Engine/indexer.py --force --embed --report
```

Windows에서 `python3`가 없다면 같은 명령을 `python.exe`로 실행하세요.

이후 일반적인 node 수정 후에는 증분 인덱싱이면 충분합니다.

```bash
python3 90_Engine/indexer.py --embed --report
```

edge 전체를 다시 풀어야 하는 경우만 `--force`를 사용합니다.

```bash
python3 90_Engine/indexer.py --force --embed --report
```

## 4. MCP 클라이언트 연결

MCP 서버는 `90_Engine/mcp_server.py`를 stdio로 실행합니다. 모든 경로는 실제 머신의 절대 경로로 바꾸세요.

Cursor (`~/.cursor/mcp.json`) 예시:

```json
{
  "mcpServers": {
    "llm-vault": {
      "command": "python3",
      "args": ["/absolute/path/to/llm-vault/90_Engine/mcp_server.py"],
      "env": {
        "VAULT_ROOT": "/absolute/path/to/llm-vault",
        "VAULT_DB": "/absolute/path/to/llm-vault/90_Engine/ltm_cache.db",
        "OLLAMA_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "bge-m3"
      }
    }
  }
}
```

Claude Desktop은 같은 `mcpServers` 구조를 사용합니다. macOS 설정 파일 위치는 보통 `~/Library/Application Support/Claude/claude_desktop_config.json`입니다.

Antigravity는 설정 파일 위치와 Windows 예시가 조금 다르므로 [docs/ANTIGRAVITY.md](docs/ANTIGRAVITY.md)를 보세요.

## 5. 연결 확인

MCP 클라이언트를 완전히 재시작한 뒤 다음 중 하나를 요청합니다.

```text
llm-vault의 vault_stats를 호출해서 현재 그래프 상태를 알려줘.
```

```text
llm-vault에서 "Vibe Coding의 위험"을 retrieve_knowledge로 검색해줘.
```

정상 연결되면 node/엣지 수나 검색 캡슐이 응답에 포함됩니다.

## 6. 운영 규칙

node edge predicate는 9개만 허용됩니다.

| Predicate | 판단 기준 |
|-----------|-----------|
| `requires` | B 없으면 A 존재 불가능 |
| `utilizes` | A가 B를 도구로 쓰지만 B 없이도 A 존재 가능 |
| `implemented_by` | 추상 명세 A가 구체 B로 실현 |
| `extends` | A가 B와 같은 층위에서 기능 추가 |
| `abstracts` | A가 B를 한 층 위에서 복잡도 감춤 |
| `causes` | A의 발생이 B를 유발 |
| `contradicts` | A와 B 양립 불가 |
| `replaces` | A가 기존 B를 기능적으로 대체 |
| `defines` | A가 B의 공식 정의 출처 |

전체 규칙은 [00_System/Ontology Specification.md](00_System/Ontology%20Specification.md)를 기준으로 합니다.

AI가 메모리를 직접 쓰는 경우의 권장 흐름은 [docs/MCP_TOOLS.md](docs/MCP_TOOLS.md)를 따릅니다.

## Troubleshooting

### `ollama: command not found`

Ollama가 설치되지 않았거나 PATH에 없습니다. 설치 후 새 터미널에서 다시 확인하세요.

### `pull model failed: bge-m3`

네트워크 연결을 확인하세요. 임시 대안으로 `ollama pull nomic-embed-text`를 사용할 수 있지만, 기본 문서와 설정은 `bge-m3` 기준입니다.

### `Ollama 응답 실패`

Ollama 서버가 꺼져 있거나 모델이 없습니다.

```bash
ollama serve
ollama pull bge-m3
```

### `[REJECT] 화이트리스트 외 술어`

9개 predicate 외 단어를 edge에 사용한 상태입니다. 온톨로지 헌법의 fallback rule에 맞춰 허용 predicate로 바꾸세요.

### MCP 클라이언트에서 도구가 안 보임

- 설정 파일의 JSON 문법을 확인합니다.
- `command`, `args`, `VAULT_ROOT`, `VAULT_DB`가 절대 경로인지 확인합니다.
- `VAULT_DB` 파일이 없으면 초기 인덱싱을 먼저 실행합니다.
- MCP 클라이언트를 완전히 종료한 뒤 다시 실행합니다.
- MCP 서버가 사용하는 Python에 `mcp` 패키지가 설치되어 있는지 확인합니다.

### Dangling edge가 남음

대상 node가 아직 없거나, 새 node 생성 후 전체 edge 재구성이 아직 실행되지 않은 상태입니다.

```bash
python3 90_Engine/indexer.py --force --embed --report
```

MCP에서는 `reconcile_graph(embed=false)` 또는 `sync_vault(force=true, embed=false)`를 사용할 수 있습니다.
