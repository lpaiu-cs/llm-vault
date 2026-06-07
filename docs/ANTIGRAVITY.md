# Antigravity 연결 가이드

이 문서는 `llm-vault`를 Google Antigravity의 MCP 서버로 연결하는 방법을 설명합니다.
연결이 끝나면 Antigravity가 vault의 node를 검색하고, 필요한 경우 MCP write 도구로 메모리를 추가·수정할 수 있습니다.

전체 도구 목록은 [MCP_TOOLS.md](MCP_TOOLS.md)를 기준으로 보세요.

## 전제 조건

- `llm-vault`가 로컬에 클론되어 있어야 합니다.
- Python 의존성이 설치되어 있어야 합니다.
- `90_Engine/ltm_cache.db`가 생성되어 있어야 합니다.
- 의미 검색을 쓰려면 Ollama와 `bge-m3` 모델이 준비되어 있어야 합니다.

예시:

```powershell
cd E:\vv\llm-vault-private
pip install -r requirements.txt
ollama pull bge-m3
python.exe 90_Engine\indexer.py --force --embed --report
```

`venv`는 필수가 아닙니다. 다만 MCP 설정의 `command`는 위 명령을 실행했을 때 사용한 Python과 같은 Python을 가리켜야 합니다.

사용 중인 Python 경로 확인:

```powershell
python.exe -c "import sys; print(sys.executable)"
```

## Antigravity MCP 설정 위치

Antigravity의 custom MCP 설정 파일:

```text
~/.gemini/config/mcp_config.json
```

Windows 예시:

```text
C:\Users\<사용자명>\.gemini\config\mcp_config.json
```

파일이 없으면 직접 만들어도 됩니다.

## 설정 예시

아래 예시는 vault 루트가 `E:\vv\llm-vault-private`인 Windows 환경입니다.
경로는 JSON에서 `/`를 쓰는 편이 안전합니다.

```json
{
  "mcpServers": {
    "llm-vault": {
      "command": "C:/Users/<사용자명>/AppData/Local/Programs/Python/Python312/python.exe",
      "args": [
        "E:/vv/llm-vault-private/90_Engine/mcp_server.py"
      ],
      "cwd": "E:/vv/llm-vault-private",
      "env": {
        "VAULT_ROOT": "E:/vv/llm-vault-private",
        "VAULT_DB": "E:/vv/llm-vault-private/90_Engine/ltm_cache.db",
        "OLLAMA_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "bge-m3"
      }
    }
  }
}
```

이미 `mcpServers`가 있는 파일이라면 전체 파일을 덮어쓰지 말고 `"llm-vault"` 항목만 추가하세요.

## 재시작 및 연결 확인

설정 저장 후 Antigravity를 완전히 종료했다가 다시 실행합니다.

채팅에서 다음처럼 요청해 연결을 확인할 수 있습니다:

```text
llm-vault MCP의 vault_stats를 호출해서 현재 node와 엣지 수를 알려줘.
```

또는:

```text
llm-vault에서 "Vibe Coding의 위험"을 retrieve_knowledge로 검색해줘.
```

정상 연결되면 vault의 node 수, 엣지 수, 검색 결과가 응답에 포함됩니다.

## GEMINI.md에 memory 사용 규칙 추가

Antigravity가 언제 vault를 조회해야 하는지 알려주려면 `~/.gemini/GEMINI.md`에 아래 섹션을 추가합니다.

```md
## llm-vault memory

- 사용자가 "내 기억", "내 기준", "이전에 정한 것", "내 node", "예전에 정리한 것"을 언급하거나 장기 지식이 필요한 질문을 하면 먼저 llm-vault MCP의 `retrieve_knowledge`를 호출한다.
- 답변에 vault 내용을 사용한 경우, 그 정보가 vault에서 온 것임을 짧게 밝힌다.
- vault에서 관련 정보를 찾지 못하면 추측하지 말고 "vault에서는 관련 기억을 찾지 못했다"고 말한다.
- 사용자가 기억을 저장하라고 명시하면 `list_notes`로 기존 제목을 확인한 뒤 `create_note`, `update_note`, `upsert_edge` 중 맞는 도구를 사용한다.
- 사람이 직접 vault 파일을 수정한 뒤에는 `sync_vault`를 호출해 인덱스를 갱신한다.
- 중요한 검색을 바로 이어서 해야 하면 `reconcile_graph`로 그래프 정합을 먼저 맞춘다.
```

`retrieve_knowledge`는 검색할 때 쓰고, 사람이 직접 파일을 편집한 뒤에는 `sync_vault`를 호출하면 됩니다. AI가 MCP write 도구로 쓴 변경은 도구 내부에서 증분 인덱싱됩니다.

## 개인 private vault로 쓰는 패턴

공개 `llm-vault`를 템플릿처럼 쓰고, 개인 기억은 private repo에서 관리할 수 있습니다.

```powershell
git clone https://github.com/lpaiu-cs/llm-vault.git llm-vault-private
cd llm-vault-private

git remote rename origin upstream
git remote set-url --push upstream DISABLED
git remote add origin https://github.com/<your-name>/llm-vault-private.git
git push -u origin main
```

이후:

- 개인 node와 기억은 `origin` private repo에 push합니다.
- 공개 템플릿 개선분은 `upstream`에서 가져옵니다.

```powershell
git fetch upstream
git merge upstream/main
```

`90_Engine/ltm_cache.db`는 로컬 캐시이므로 커밋하지 않는 것이 좋습니다.

## Troubleshooting

### 도구가 보이지 않음

- `mcp_config.json` 위치가 `~/.gemini/config/mcp_config.json`인지 확인합니다.
- JSON 문법 오류가 없는지 확인합니다.
- Antigravity를 완전히 재시작합니다.

### `ModuleNotFoundError: mcp`

MCP 서버가 실행하는 Python에 의존성이 설치되어 있지 않은 상태입니다.

```powershell
python.exe -m pip install -r requirements.txt
python.exe -c "import mcp; print('mcp ok')"
```

그 다음 `mcp_config.json`의 `command`가 같은 Python 실행 파일을 가리키는지 확인합니다.

### `ltm_cache.db`가 없다는 오류

먼저 인덱서를 실행해 DuckDB 캐시를 생성합니다.

```powershell
python.exe 90_Engine\indexer.py --force --embed --report
```

### Ollama embedding 오류

Ollama 서버와 모델을 확인합니다.

```powershell
ollama list
ollama pull bge-m3
```

Ollama가 꺼져 있다면:

```powershell
ollama serve
```
