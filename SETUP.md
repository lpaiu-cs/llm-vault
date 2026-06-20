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

### 범용 MCP 클라이언트 (Codex, Windsurf, Cline 등)

`90_Engine/mcp_server.py`는 표준 **stdio MCP 서버**라 MCP를 지원하는 거의 모든
클라이언트에 붙습니다. 설정의 본질은 4가지로 동일하고, 클라이언트마다 **설정 파일
위치와 포맷만** 다릅니다.

- `command`: 의존성(`mcp`, `duckdb`, `rank-bm25`)이 설치된 Python (예: `<REPO>/.venv/bin/python`)
- `args`: `["<REPO>/90_Engine/mcp_server.py"]`
- `env`: `VAULT_ROOT`, `VAULT_DB`, `OLLAMA_URL`, `OLLAMA_MODEL`
- transport: `stdio`

**JSON `mcpServers` 계열** — Cursor(`~/.cursor/mcp.json`), Claude Desktop, Claude Code
(`.mcp.json`), Windsurf, Cline, Antigravity 등은 위 Cursor 예시와 **동일 구조**이며 파일
위치만 다릅니다.

**OpenAI Codex CLI** — TOML(`~/.codex/config.toml`)을 씁니다:

```toml
[mcp_servers.llm-vault]
command = "<REPO>/.venv/bin/python"
args = ["<REPO>/90_Engine/mcp_server.py"]

[mcp_servers.llm-vault.env]
VAULT_ROOT = "<REPO>"
VAULT_DB = "<REPO>/90_Engine/ltm_cache.db"
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "bge-m3"
```

공통 주의:

- `command`는 반드시 의존성이 깔린 Python이어야 합니다. 시스템 `python3`에 `mcp`/`duckdb`가
  없으면 이 저장소의 `.venv/bin/python`을 쓰세요.
- 경로는 절대 경로를 권장합니다. `VAULT_DB`가 없으면 먼저 인덱싱(§3)하세요.
- 클라이언트/버전마다 키가 다를 수 있습니다(예: `mcpServers`(JSON) vs `mcp_servers`(TOML)).
  세부는 해당 클라이언트 문서를 확인하세요. Ollama 미가동 시 자동으로 BM25-only로 동작합니다.

### Claude Code (CLI/IDE) 연결

Claude Code는 **프로젝트 루트의 `.mcp.json`을 자동 인식**합니다(첫 사용 시 승인 프롬프트).
`command`는 의존성이 설치된 Python(예: 이 저장소의 `.venv`)을, `args`는 서버 스크립트를
가리킵니다.

저장소에 포함된 [`.mcp.json.example`](.mcp.json.example)을 복사해 **절대경로 2곳만** 고치면 됩니다:

```bash
cp .mcp.json.example .mcp.json
# .mcp.json 을 열어 command/args 의 <REPO> 를 이 기기의 저장소 절대경로로 치환
```

```json
{
  "mcpServers": {
    "llm-vault": {
      "command": "<REPO>/.venv/bin/python",
      "args": ["<REPO>/90_Engine/mcp_server.py"]
    }
  }
}
```

`env` 블록은 **생략 가능**합니다 — 서버가 `mcp_server.py`의 위치에서 `VAULT_ROOT`/`VAULT_DB`를,
기본값에서 `OLLAMA_URL`(localhost:11434)/`OLLAMA_MODEL`(bge-m3)을 스스로 유도합니다. 바꾸고
싶을 때만 `env`로 덮어쓰세요.

> **왜 `.mcp.json`을 커밋하지 않나(`.gitignore`)?** 비밀값이라서가 아니라, `.mcp.json`이
> **절대경로만** 허용하기 때문입니다(상대경로는 에러, `${CLAUDE_PROJECT_DIR}`는
> project-scoped 파일의 command/args에서 신뢰성 있게 확장되지 않음). 그 절대경로가
> 기기·OS마다 다르므로(특히 `.venv/bin` vs `.venv\Scripts`) 커밋하면 다른 기기에서
> 깨집니다. 그래서 머신 로컬로 두고 `.example`만 공유합니다.

또는 터미널에서 한 줄로 등록(사용자 스코프, `env`는 기본값을 바꿀 때만):

```bash
claude mcp add llm-vault -- <REPO>/.venv/bin/python <REPO>/90_Engine/mcp_server.py
# 기본값을 바꾸려면 끝에 --env KEY=VAL 추가(예: --env OLLAMA_MODEL=다른모델)
```

등록 후 Claude Code를 재시작하면 `retrieve_knowledge`, `review_queue`, `vault_stats`,
`create_note` 등이 노출됩니다. 상태는 `/mcp`로 확인합니다.

> ⚠️ **`.mcp.json`은 복사만으론 부족합니다.** `cp .mcp.json.example .mcp.json` 후
> ① `<REPO>` 치환 ② `.venv` 실제 생성(venv+requirements) ③ `ltm_cache.db` 빌드(§3
> 인덱싱; 없으면 MCP 서버가 "캐시 없음"으로 시작 실패) ④ Claude Code 재시작이 모두
> 필요합니다.
>
> ⚠️ **Windows 경로 주의.** venv 파이썬이 `bin/`이 아니라 `Scripts/`에 있습니다.
> `command`를 `<REPO>\.venv\Scripts\python.exe`로 쓰고(즉 `.venv/bin/python` ❌),
> JSON 안에서는 경로 구분자를 `\\`로 이스케이프하세요:
>
> ```jsonc
> "command": "C:\\Users\\me\\llm-vault-private\\.venv\\Scripts\\python.exe",
> "args": ["C:\\Users\\me\\llm-vault-private\\90_Engine\\mcp_server.py"],
> ```

### 다중 기기 설정 (clone 후 매 기기 1회)

**동기화는 git 하나로 단일화합니다.** vault(마크다운)는 git으로 옮기고, **파생물은
기기마다 새로 만듭니다**(아래는 모두 `.gitignore` 대상). 새 기기에서:

```bash
git clone <repo-url> && cd llm-vault
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# (선택) 더 견고한 YAML 파싱: .venv/bin/pip install pyyaml
brew install ollama && brew services start ollama && ollama pull bge-m3   # macOS
.venv/bin/python 90_Engine/indexer.py --vault . --db 90_Engine/ltm_cache.db --embed --force --report
cp .mcp.json.example .mcp.json   # <REPO> 를 이 기기 경로로 치환 후 Claude Code 재시작
```

`ltm_cache.db`(임베딩 포함)·`.venv`·`.mcp.json`은 동기화하지 않습니다. node_id 등
그래프 정체성은 마크다운 frontmatter에 들어 있어 git으로 함께 옮겨지므로, 각 기기에서
인덱싱만 다시 하면 동일한 그래프가 재생성됩니다.

> ⚠️ **git 위에 다른 파일 동기화 도구를 겹치지 마세요.** vault 폴더를 Obsidian Sync,
> iCloud, Dropbox, OneDrive 등으로 동시에 동기화하면 `.git` 내부와 DuckDB 캐시
> (`*.db`/`*.db.wal`)가 두 동기화 주체 사이에서 손상·충돌됩니다. 기기 간 이동은 항상
> `git pull` / `git push` 로만 하고, 작업 전후로 커밋·동기화하는 습관을 들이세요.
> (충돌 방지를 위해 DB는 절대 추적하지 않으며, 각 기기에서 재인덱싱으로 만듭니다.)

### 자동 동기화 (선택)

매번 `git add/commit/push`를 직접 치기 번거롭고, 사실상 "개인 클라우드"로만 쓴다면
동기화 스크립트가 **자동 커밋(타임스탬프+호스트명) → pull --rebase → push**를 한 번에
처리합니다. 커밋 메시지를 매번 쓸 필요가 없습니다.

- **mac / Linux:** [`scripts/sync.sh`](scripts/sync.sh) (bash)
- **Windows:** [`scripts/sync.ps1`](scripts/sync.ps1) (PowerShell)

```bash
scripts/sync.sh            # mac/linux: 자동 메시지로 동기화
scripts/sync.sh "메모"      # 메시지를 직접 주고 싶을 때
```
```powershell
powershell -ExecutionPolicy Bypass -File scripts\sync.ps1     # Windows
```

- **origin(private)에만 push합니다.** 공개 템플릿(upstream)에는 절대 보내지 않습니다
  (공개 반영은 항상 [`scripts/sync-template.sh`](scripts/sync-template.sh)로만).
- 커밋 로그가 `sync: ...`로 길어지지만, private는 "동기화 저널"이라 무방합니다. 공개
  템플릿 히스토리는 `sync-template.sh`로 큐레이션되어 깨끗하게 유지됩니다.
- rebase 충돌은 자동 해결하지 않고 멈춥니다(데이터 안전 우선) — 안내대로 수동 처리.

**완전 자동(스케줄러).** 손 안 대고 일정 간격(기본 15분)으로 돌리려면 OS별 스케줄러에
등록합니다. 모두 **로그인 시 + 15분마다** 실행하며, Obsidian이 꺼져 있어도(=Claude
Code/MCP로만 작업해도) 동기화됩니다.

*macOS (launchd)* — [`scripts/launchd/com.llm-vault-sync.plist.example`](scripts/launchd/com.llm-vault-sync.plist.example):

```bash
cp scripts/launchd/com.llm-vault-sync.plist.example \
   ~/Library/LaunchAgents/com.example.llm-vault-sync.plist
# 편집기로 열어 <REPO>/<HOME> 치환 후:
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.llm-vault-sync.plist
launchctl list | grep llm-vault                    # 등록 확인
tail -f ~/Library/Logs/llm-vault-sync.log
```

*Linux (systemd user)* — [`scripts/systemd/`](scripts/systemd) (`.service` + `.timer`):

```bash
mkdir -p ~/.config/systemd/user
cp scripts/systemd/llm-vault-sync.service.example ~/.config/systemd/user/llm-vault-sync.service
cp scripts/systemd/llm-vault-sync.timer.example   ~/.config/systemd/user/llm-vault-sync.timer
# 두 파일의 <REPO> 치환 후:
systemctl --user daemon-reload
systemctl --user enable --now llm-vault-sync.timer
loginctl enable-linger "$USER"                     # 로그아웃 상태에서도 동작
systemctl --user list-timers | grep llm-vault      # 등록 확인
journalctl --user -u llm-vault-sync.service -f      # 로그
```

*Windows (작업 스케줄러)* — [`scripts/windows/register-task.ps1`](scripts/windows/register-task.ps1)
가 경로를 자동 인식해 등록합니다(치환 불필요, 관리자 권한 불필요):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\register-task.ps1
Get-ScheduledTaskInfo -TaskName 'llm-vault-sync'    # LastRunResult 확인
# 제거: Unregister-ScheduledTask -TaskName 'llm-vault-sync' -Confirm:$false
```

> ⚠️ 자동 실행을 켜면 **첫 실행이 그 시점의 미커밋 변경을 전부 자동 커밋**합니다(클라우드
> 동기화 취지상 의도된 동작). 진행 중인 작업을 따로 정리하고 싶다면 켜기 전에 정리하세요.
>
> 자격증명은 **비대화식**이어야 합니다(백그라운드라 프롬프트 불가): macOS Keychain,
> Windows Git Credential Manager, Linux는 libsecret/PAT 또는 SSH 키 + ssh-agent.

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

## 7. 검색 정책과 평가 (선택)

검색은 계층/신뢰도 인지입니다. 랭킹 가중치·필터·주석은
[00_System/Retrieval Policy.yaml](00_System/Retrieval%20Policy.yaml)에서 로드됩니다(없으면
retriever 내장 fallback). PyYAML이 있으면 사용하고, 없으면 내장 최소 파서로 읽으므로
추가 설치는 선택입니다(`pip install pyyaml`).

이 가중치는 **잠정적 사전값(provisional prior)**입니다. 검색 품질을 측정·튜닝하려면:

```bash
python3 90_Engine/eval_retrieval.py \
  --db 90_Engine/ltm_cache.db \
  --queries 90_Engine/eval_queries.sample.json
```

`MRR@5`, `Recall@5`, `review_leakage_rate`(검토 계층 누수=기본 0), `raw_overexposure_rate`
(원본 과다노출)를 보고 `Retrieval Policy.yaml`을 조정하세요. 자세한 내용은
[40_Decisions/2026-06-18-layer-and-confidence-aware-retrieval.md](40_Decisions/2026-06-18-layer-and-confidence-aware-retrieval.md).

## 8. public 템플릿 vs private 인스턴스

이 프로젝트는 **두 개의 별개 레포**로 운영합니다. 역할이 다릅니다.

- **public `llm-vault` (`upstream`) = 프레임워크 템플릿** — 누구나 scratch에서 시작할 수
  있는 골격입니다. 담는 것: 엔진(`90_Engine/`) + 정책(`00_System/`) + 문서/스크립트 +
  **빈 vault 스켈레톤**(지식 계층은 `README/.gitkeep`만) + `examples/mini-vault/`(데모).
  실제 지식 코퍼스는 담지 않습니다.
- **private `llm-vault-private` (`origin`) = 실제 second brain 인스턴스** — 당신의 진짜
  지식이 `10_MOC/`·`20_Concepts/`·`30_Projects/`·`40_Decisions/`·`50~80`에 쌓이는 곳.
  개인 데이터는 **오직 여기에만** 둡니다.

```bash
git push                          # origin(private)로 백업 (실제 지식 포함 OK)
scripts/sync-template.sh <커밋…>   # 프레임워크 개선만 골라 upstream(public)에 반영
```

**경계 (allowlist 기준 — "기본 차단, 명시적 허용"):**

공개 허용 경로는 [`scripts/template-allowlist.txt`](scripts/template-allowlist.txt)에
명시되어 있고, 동기화 스크립트는 **여기에 없는 경로가 하나라도 섞이면 push를 중단**합니다.

| 구분 | 경로 | allowlist |
|------|------|-----------|
| 프레임워크 (공개) | `90_Engine/`, `docs/`, `scripts/`, `00_System/`, `examples/`, 루트 문서(`README/SETUP/AGENTS/LICENSE/requirements`) | 등록 → 허용 |
| vault 스켈레톤 (공개) | 모든 지식 계층의 `README.md`·`.gitkeep` **만** | 등록 → 허용 |
| 실제 지식 (private 전용) | `10_MOC/`·`20_Concepts/`·`30_Projects/`·`40_Decisions/`·`50~80`의 **모든 콘텐츠 파일**, `05_Inbox/`·`06_Raw/` 콘텐츠 | 미등록 → **기본 차단** |

즉 지식 계층은 **디렉터리 통째 허용이 없습니다.** 어떤 계층에 무엇을 적든 콘텐츠 파일은
기본 차단되므로, public에 노출하려면 의식적인 결정이 필요합니다. 공개용 예시는
`examples/mini-vault/`에 최소한만 둡니다(README/.gitkeep 외 실제 노트는 main vault에 두지 않음).

> **structure 분기 운영**: public main vault를 스켈레톤으로 유지하면서 private main vault에는
> 실제 지식을 쌓으려면, public 정리는 private 워킹카피가 아니라 별도 worktree에서 합니다.
> `git worktree add -b public-main ../llm-vault-public upstream/main` 후 거기서 스켈레톤/예시를
> 관리하고 upstream에 push합니다. private main을 비우는 커밋은 만들지 않습니다.

**원칙:**

- 템플릿 변경과 개인 데이터를 **별도 커밋**으로 분리하면 선별 반영(cherry-pick)이 깔끔합니다.
- 개인 데이터가 생긴 뒤에는 **`git push upstream main`을 직접 하지 마세요**(유출 위험).
  반드시 `scripts/sync-template.sh`를 쓰세요. 가드는 2단계입니다:
  1. **allowlist** — 변경 파일이 `template-allowlist.txt`에 없으면 중단(1차 방어).
  2. **denylist** — `05_Inbox/06_Raw/50_Source_Summaries` 콘텐츠는 재차 명시적 차단(보조).
- 공개할 새 파일이 늘면 `template-allowlist.txt`에 추가하기 전에 "정말 개인정보가
  없는가?"를 먼저 확인하세요. 매칭 규칙은 `scripts/test-template-allowlist.sh`로 검증합니다.

```bash
# 먼저 push 없이 가드만 점검(권장)
scripts/sync-template.sh --dry-run 174e250
# 통과하면 실제 반영
scripts/sync-template.sh 174e250
```

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

### `[ABORT] allowlist에 없는 경로가 있어 공개 push를 중단합니다`

`scripts/sync-template.sh`의 1차 가드입니다. 동기화하려는 커밋에 공개 허용 목록
([`scripts/template-allowlist.txt`](scripts/template-allowlist.txt))에 없는 경로가
포함됐다는 뜻입니다. 출력된 파일이 **개인 데이터면** 해당 커밋을 동기화 대상에서 빼고
(템플릿 변경만 별도 커밋으로 분리), **정말 공개해도 되는 템플릿 파일이면** allowlist에
한 줄 추가한 뒤 다시 실행하세요. 추가 전에 `scripts/test-template-allowlist.sh`로
규칙을 점검할 수 있습니다.

### `Constraint Error: ... still referenced by a foreign key`

예전 스키마(edges에 FK가 있던 버전)로 만든 `ltm_cache.db`에서 임베딩/메타 UPDATE 시
발생합니다. DuckDB의 FK UPDATE 한계 때문이며, 현재 스키마는 FK를 제거했습니다.
캐시는 재생성 가능하므로 DB를 지우고 다시 빌드하세요.

```bash
rm -f 90_Engine/ltm_cache.db*
python3 90_Engine/indexer.py --force --embed --report
```

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
