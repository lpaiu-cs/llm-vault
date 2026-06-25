# 데몬 자동 기동 버그 — 발견·원인·수정 보고

**대상:** `vault_daemon.py` / `daemon_client.py` / `mcp_server.py` 데몬 레이어 작성자
**환경:** Windows 11, Claude Code(데스크톱) + Codex + Antigravity가 같은 vault를 MCP로 사용
**커밋:** `36fea5db9154c0c00f6ba465c6a0b573583cd6d3` (`36fea5d`, origin/main 반영됨) — `daemon_client.py` 한 곳 수정
**작성일:** 2026-06-25

---

## 1. 한 줄 요약

`USE_DAEMON=1`로 켜도 **Windows에서 데몬이 한 번도 안 떠 있고 프록시가 영구히 in-process 폴백**으로만 동작했다. 원인은 `ensure_daemon`이 데몬을 `sys.executable`로 spawn하는데, Windows venv 런처가 base 파이썬으로 redirect되면서 그 `sys.executable`이 **venv가 아닌 base `Python312`** 를 가리켰고, base에는 `duckdb`/`fastapi`가 없어 데몬이 import 단계에서 즉사했기 때문. `sys.prefix` 기반으로 venv 인터프리터를 도출해 spawn하도록 고쳤다.

## 2. 증상 (왜 눈에 안 띄었나)

- MCP 툴(`retrieve_knowledge`, `vault_stats`)은 **정상적으로 결과를 반환**했다 → 겉보기엔 데몬이 잘 동작하는 것처럼 보였다.
- 그러나 실제로는 `mcp_server.py`의 **in-process 폴백 경로**가 응답한 것이었다(`_daemon_call`이 실패 → `if not USE_DAEMON` 아래 직접 retrieve).
- `daemon_client.health(41514)`는 계속 `None`, `netstat`에 `:41514 LISTENING` 없음.
- `vault_daemon.py` 프로세스는 떠 있는 것처럼 보였지만(작업관리자) **포트에 바인드되지 않은 채** 남아 있었다.

> 폴백이 조용히 성공하기 때문에, 데몬이 **완전히 죽어 있어도** 사용자/호출자는 알 수 없다. 이게 진단을 가장 어렵게 만든 지점이다.

## 3. 근본 원인

`ensure_daemon`(`daemon_client.py`)의 spawn:

```python
subprocess.Popen([sys.executable, script], **kwargs)   # 수정 전
```

- 프록시(`mcp_server.py`)는 MCP 설정의 `command = .../.venv/Scripts/python.exe`로 기동된다.
- 그런데 이 기기에서는 venv의 `Scripts/python.exe`가 **base `Python312`로 재실행(redirect)** 된다(프로세스 트리: `venv/Scripts/python.exe` → 자식 `...\Python312\python.exe ...mcp_server.py`). 이건 venv 생성 방식/런처 stub에 따른 Windows 특유 동작이다.
- 그 결과 **프록시 프로세스 내부의 `sys.executable`이 base `Python312`** 가 된다(venv site-packages는 `pyvenv.cfg`의 home을 통해 활성화돼 있어 프록시 자신은 duckdb를 쓸 수 있음 — 그래서 in-process 폴백은 멀쩡히 동작).
- `ensure_daemon`이 그 `sys.executable`(=base)로 새 프로세스를 띄우면, 그 프로세스는 venv 활성화 컨텍스트 없이 **base의 site-packages**만 본다. base에는 `duckdb`가 없어:

```
$ <base python> vault_daemon.py
ERROR: duckdb 미설치. pip install duckdb
```

→ `import retriever`(→duckdb) 단계에서 즉사. `ensure_daemon`은 `wait`(20s) 동안 `/health` 폴링하다 `None` 반환 → 프록시는 폴백.

## 4. 진단에 쓴 결정적 방법

- **데몬 경유 여부 판별:** 라이브 MCP 툴을 호출한 직후 `health(41514)`의 `graph_loaded`를 본다.
  - `false → true`로 바뀌고 `node_count`가 채워지면 → **데몬이 그 쿼리를 처리**(get_retriever가 인메모리 그래프 적재).
  - 안 바뀌면 → 프록시가 in-process 폴백.
- **데몬 spawn 실패 재현:** `ensure_daemon`은 데몬 stdout/stderr를 `DEVNULL`로 버린다. 그래서 base 파이썬으로 `vault_daemon.py`를 **직접** 실행해 stderr를 파일로 받자마자 `ERROR: duckdb 미설치`가 바로 드러났다.
- **인터프리터 차이 확인:**
  - `venv python -c "import sys; print(sys.executable, sys.prefix)"` → executable=venv, prefix=venv.
  - base `Python312`에는 duckdb 없음(단, fastapi는 우연히 둘 다 설치돼 있어 fastapi는 원인이 아니었다).
  - `Path(sys.prefix)/Scripts/python.exe`는 venv가 활성인 한 항상 venv 인터프리터를 가리키고, 거기엔 duckdb 1.5.3 존재.

## 5. 수정 (commit `36fea5d`)

`daemon_client.py`:

```python
def _venv_python() -> str:
    """데몬을 띄울 인터프리터. sys.executable을 쓰면 안 되는 이유: Windows venv 런처는
    base 파이썬으로 redirect되는 경우가 있어(프록시가 venv/Scripts/python.exe로 기동돼도
    sys.executable이 base Python을 가리킴), 그 base에는 venv 의존성(duckdb/fastapi)이 없어
    데몬이 import에서 즉사한다. sys.prefix는 pyvenv.cfg로 항상 active venv를 가리키므로,
    거기서 venv 인터프리터를 도출한다. venv가 아니면(=경로 부재) sys.executable로 폴백."""
    if os.name == "nt":
        cand = Path(sys.prefix) / "Scripts" / "python.exe"
    else:
        cand = Path(sys.prefix) / "bin" / "python"
    return str(cand) if cand.exists() else sys.executable

# ensure_daemon 내부
-    subprocess.Popen([sys.executable, script], **kwargs)
+    subprocess.Popen([_venv_python(), script], **kwargs)
```

`sys.prefix`는 venv가 활성일 때(프록시가 venv로 기동된 경우) 항상 venv 루트를 가리키므로, redirect로 `sys.executable`이 base가 돼도 올바른 venv 인터프리터로 데몬을 띄운다. venv가 아니면 경로가 없어 `sys.executable`로 폴백 → 비-venv 환경은 영향 없음.

**검증:** 수정 후 프록시가 데몬을 정상 기동, `:41514` LISTENING, 라이브 `vault_stats`/`retrieve_knowledge` 호출 시 `graph_loaded=true`/`node_count=72` 확인.

## 6. 권고 (작성자 판단용 — 미반영)

1. **무음 폴백을 관측 가능하게.** in-process 폴백이 조용히 성공해서 데몬 완전 실패를 가렸다. spawn 실패 시 한 줄이라도 흔적을 남기길 권함 — 예: `ensure_daemon`이 실패하면 stderr 대신 로그파일(`90_Engine/daemon.spawn.log`)로 리다이렉트하거나, `DAEMON_DEBUG=1`일 때 `DEVNULL` 대신 파일로 캡처. `/health`에 "last_spawn_error" 같은 필드도 후보.
2. **인터프리터를 추정 대신 명시.** 프록시는 자신이 어떤 `command`로 떠야 하는지 MCP 설정에 이미 있다. `sys.prefix` 도출이 깔끔한 1차 해법이지만, 더 견고하게는 프록시가 자신의 기동 인터프리터(또는 `VAULT_PY` 같은 env)를 `ensure_daemon`에 명시 전달하는 것도 고려.
3. **spawn 경합 시 패배 데몬 정리.** 여러 클라이언트가 동시에 첫 호출을 하면 데몬이 동시에 여러 개 spawn될 수 있다. 정상 코드에선 바인드 진 쪽이 uvicorn 에러로 종료되지만, (이번처럼) import 단계에서 죽으면 `main()`의 싱글턴 체크에 도달조차 못 한다. 수정 후엔 크래시가 없어 재발 안 하지만, 안전망으로 "이미 healthy면 즉시 종료" 체크를 import 직후 한 번 더 두는 것도 방어적.
4. (참고) `fastapi`는 base/venv 양쪽에 있어 원인이 아니었다. 핵심 누락 의존성은 `duckdb`. 의존성은 venv에만 보장되므로, 데몬은 반드시 venv 인터프리터로 떠야 한다는 불변식이 핵심.

## 7. 곁가지(이번 셋업 한정, 데몬 무관)

- 활성화는 클라이언트별 env 한 줄(`USE_DAEMON="1"`): Claude=`~/.claude.json`, Antigravity=`~/.gemini/config/mcp_config.json`, Codex=`~/.codex/config.toml`. 데몬은 머신당 싱글턴(포트 41514)이라 셋이 1개를 공유.
- 이 레포는 Claude Code에서 `.mcp.json`(프로젝트 스코프)을 `.claude/settings.local.json`의 `disabledMcpjsonServers`로 비활성화하고 `~/.claude.json`(유저 스코프)만 쓴다(중복 등록 회피). 다른 IDE는 `.mcp.json`을 그대로 사용.
