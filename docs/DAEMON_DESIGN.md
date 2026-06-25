# llm-vault Engine — Daemon Architecture (구현 완료: M1–M3)

> 상태: **구현 완료 · main 반영**. M1(read 포워딩)·M2(write 소유)·M3(이벤트 구동 git sync)이
> 머지됐고, Windows venv-인터프리터 spawn 버그가 후속 수정됨
> ([handoff/DAEMON_SPAWN_FIX.md](../handoff/DAEMON_SPAWN_FIX.md)). 기본은 in-process이며
> 데몬은 `USE_DAEMON=1`로 opt-in한다(사용자 설정: SETUP.md '데몬 모드' 절). 결정 사항은 §11.
> 관련: [[2026-06-25-llm-vault-engine-concurrency-snapshot-writes]],
> [[2026-06-21-cross-device-sync-via-git]].

## 0. 배경 · 목표

**배경.** 현재 동시성 모델은 Phase 1(단명 read-only 연결) + Phase 3(immutable snapshot +
`os.replace` 원자 교체)다. Phase 3는 POSIX 의미론(열린 파일 위 rename, 열린 fd가 unlink된
inode 유지, `flock` 크래시 자동해제)에 의존해 **Windows에서 성립하지 않는다**. 사용자는
macOS와 Windows를 git-sync로 **동시 작업 볼트**로 쓴다. `ltm_cache.db`는 gitignore라
**머신마다 따로** 생성되므로, 실제 문제는 "한 머신 안 N개 MCP 프로세스가 로컬 DB 하나를
두고 경합"이고 이게 **양 OS에서** 성립해야 한다.

**목표.**
- 머신마다 **단일 소유자 데몬**이 DB를 독점 → 다중 프로세스 파일 경합 자체를 제거.
- **localhost HTTP** 전송(Win/mac/Linux 동일). 데몬 **자동 기동 + idle 자동 종료(옵션)**.
- **이벤트 구동 싱크**(write 후 push 디바운스 / 요청 시 stale면 pull) — 타이머·OS 스케줄러 불요.
- 코어 **단순화**: snapshot/flock/WAL/os.replace 제거.

**비목표.** 머신 간 DB 공유(계속 per-machine), Markdown=source-of-truth 불변, 온톨로지·검색
로직 변경 없음.

## 1. 아키텍처

```
[Claude]   [Codex]   [Antigravity]        ← MCP 클라이언트 (머신당 N개)
   │          │            │
   ▼ stdio    ▼ stdio      ▼ stdio
mcp_server  mcp_server  mcp_server         ← 얇은 프록시(상태 無, DB 미접근)
   │          │            │
   └──────────┴─ HTTP 127.0.0.1:PORT ──────┘
                     │
                     ▼
              vault_daemon (머신당 1개, 싱글턴)
              ├─ 인메모리 그래프 (1회 적재)
              ├─ DuckDB 접근 (소유, 직렬화된 write)
              ├─ indexer (증분 + orphan prune)
              └─ git 싱크 에이전트 (이벤트 구동)
                     │
                     ▼
            ltm_cache.db (로컬)  +  Markdown(vault)  +  git remote
```

머신당 데몬 1개 = DB 소유자 = 싱크 주체. 프록시는 무상태라 클라이언트가 띄우고 죽이는
대로 와도 무방하다. **DB를 만지는 프로세스가 하나뿐**이라 OS 파일락/rename 문제가 전부 소멸.

## 2. 데몬 (`90_Engine/vault_daemon.py`)

- **HTTP 서버**: FastAPI + uvicorn (이미 설치·requirements에 선언, retriever.py §8 스캐폴딩 연장).
  단일 워커(`workers=1`). 데몬 도입 시 fastapi/uvicorn/pydantic은 **선택 → 필수**로 승격.
- **소유 자원**: 인메모리 그래프(nodes/edges), DuckDB 단일 인스턴스 연결 1개, indexer, sync 상태.
- **동시성 모델(베이스라인)**:
  - 읽기 — 인메모리 그래프에서 처리, dense cosine SQL만 소유 연결로 실행.
  - 쓰기 — **in-process 락(asyncio/threading)으로 직렬화**, 같은 소유 연결로 in-place 수행.
  - 단일 프로세스라 같은 파일에 두 번째 `duckdb.connect`을 열지 않음 → 프로세스 내 락 충돌 없음.
  - (최적화 여지: read 전용 cursor 분리. M1에서 연결/커서 모델 확정.)
- **캐시**: 그래프는 기동 시(또는 첫 요청 시) 1회 적재, write/pull 후 무효화·재적재.

## 3. 프록시 (`mcp_server.py`를 얇게)

- 각 MCP 도구 = 데몬 HTTP로 포워딩 후 JSON 반환. 프록시는 DB·그래프를 갖지 않음.
- **데몬 보장**: 호출 시 `/health` 확인 → 다운이면 데몬을 **detached 자식으로 기동**
  (POSIX `setsid`, Windows `DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP`) → `/health` ready까지 폴링.
- **폴백**: 데몬에 닿지 못하고 요청이 **읽기**(retrieve/vault_stats/review_queue)면, 프록시가
  **직접 단명 read-only 연결**로 응답(Phase 1 경로, degraded). 쓰기는 데몬 필수 — 기동 실패 시
  명확한 tool error.
- stdout 규율 유지(로그는 stderr; JSON-RPC 채널 오염 금지).

## 4. 라이프사이클

- **싱글턴 + 디스커버리**: 데몬은 vault-경로 해시 기반 결정적 포트(예: `40000 + hash(VAULT_DB)%2000`)
  바인드. `EADDRINUSE`면 기존 데몬 추정 → `/health` 확인 후 정상이면 종료(중복 방지), 비정상이면
  포트파일 정리 후 재시도. 바인드 성공 시 **portfile**(`<db>.daemon.json` = {port,pid,started_at})
  기록 → 프록시가 이걸로 포트 발견.
- **자동 기동 레이스**: 동시 기동된 둘째 데몬은 bind 실패로 즉시 종료 → 항상 1개 생존. 포트 바인드가
  레이스 해소기.
- **idle 자동 종료(옵션, 기본 off = 상시가동)**: 기본은 상시 데몬(수 MB 상주, 부담 적음).
  `idle_shutdown=on`이면 마지막 활동시각 추적 → `idle_timeout`(기본 30분) 동안 in-flight 요청·미완
  push 없으면 clean shutdown(portfile 제거), 다음 요청이 재기동.
  - **이벤트 구동 싱크 덕에 종료와 싱크가 충돌하지 않음**(싱크는 활동 시에만 발생).

## 5. 이벤트 구동 싱크

방향을 분리한다(요청 없음 → 변경 없음 → push 불요; 단 pull은 타 머신 변경 수신용).

- **Push** = 로컬 write(create/update/delete/edge) 성공 후 **디바운스 commit+push**
  (마지막 write 후 `push_debounce`초, 기본 30–60s). 버스트 = 1회 push. 빈 커밋 없음.
- **Pull** = 요청 서빙 직전, `last_pull`이 `pull_throttle`(기본 2–5분) 초과면 1회 `git pull`
  (fetch + rebase) → 변경 파일 있으면 **증분 reindex** → 그 후 서빙. throttle로 연속 요청 시 매번 X.
  실패(네트워크 등)면 로그 + 현재 캐시로 서빙.
- **충돌 정책**: pull 충돌 시 **자동 해결 금지** — `rebase --abort`, `health.sync_status=conflict`로
  표면화 + 자동 pull 중단(사용자 해소까지), 파괴적 조치 금지. push 거부(non-fast-forward)는
  pull-rebase 후 1회 재시도, 그래도 실패면 표면화.
- **git 격리**: 모든 git은 **서브프로세스 + 하드 타임아웃**, 백그라운드 태스크로. 요청 서빙 경로를
  절대 블록하지 않음.
- **인증**: git credential helper 의존(mac keychain / Windows GCM / SSH agent). 셋업은 SETUP.md에 문서화.
- **옵션**: `background_pull_interval`(기본 0=off) — idle 중 선제적 최신화를 원할 때만.
- 기존 launchd 잡 / `sync-template.sh`의 **스케줄링 역할을 대체**(커밋 템플릿은 수동/public용으로 유지 가능).

## 6. 제거 / 유지

- **제거(데몬이 DB 소유 후)**: `_build_lock`, `_snapshot_build`, WAL fold, `os.replace` swap,
  `fcntl`/O_EXCL 분기 — 다중 프로세스 단일소유 흉내 장치 일체. → 코어 순감소.
- **유지**: retriever(단명 read-only `connect_db`는 데몬 read 경로 + 프록시 read 폴백으로 재활용),
  indexer(증분 + orphan prune + `connect_db` dedup), 검색·온톨로지 로직 전부, Phase 1 단명 읽기.

## 7. 설정

env(기존 VAULT_DB/VAULT_ROOT/OLLAMA_* 연장) 또는 `00_System` 설정 파일:

| 키 | 기본 | 의미 |
|---|---|---|
| `DAEMON_PORT` | 결정적(해시) | 비우면 vault 해시 기반 |
| `DAEMON_IDLE_SHUTDOWN` | `false` | 기본 상시가동; on이면 idle 자동 종료 |
| `DAEMON_IDLE_TIMEOUT` | `1800s` | idle 종료 임계(활성 시, 30분) |
| `SYNC_ENABLED` | `true` | 데몬 싱크 on/off |
| `SYNC_PUSH_DEBOUNCE` | `45s` | write 후 push 지연 |
| `SYNC_PULL_THROTTLE` | `180s` | 요청 시 pull 최소 간격 |
| `SYNC_BACKGROUND_PULL_INTERVAL` | `0`(off) | 선제적 pull 타이머 |
| `GIT_TIMEOUT` | `60s` | git 서브프로세스 타임아웃 |
| `USE_DAEMON` | (롤아웃) | 프록시가 데몬 경유 여부(롤백용 플래그) |

## 8. 크로스플랫폼

- HTTP localhost: 동일. **단일 소유자라 OS 파일락 불필요** → fcntl/msvcrt 문제 자체가 사라짐.
- 프로세스 기동: subprocess + OS별 detach 플래그.
- git: 서브프로세스 + OS별 credential helper. paths는 pathlib.
- Windows 실기 검증 항목: detach 플래그, git 인증, 폴백 read 경로(§11).

## 9. 단계적 롤아웃 (각 단계: 테스트 → private 배포 → 라이브 검증, `USE_DAEMON` 플래그로 롤백 가능)

- **M1 — 읽기 데몬 + 프록시 골격.** vault_daemon: `/health`, `/retrieve`, `/vault_stats`,
  자동 기동/싱글턴/idle 종료. 프록시: 읽기 포워딩 + 데몬-다운 read 폴백. 쓰기는 아직 현 경로.
  검증: 다중 클라이언트 읽기, **그래프 1회 적재**, 락 에러 0.
- **M2 — 쓰기 데몬 + snapshot 제거.** create/update/delete/edge/sync/reconcile 엔드포인트 +
  프록시 포워딩. in-process write 직렬화. `_snapshot_build`/`_build_lock`/WAL/os.replace 삭제.
  검증: write+read 일관성, 다중 클라이언트 동시 write 직렬화.
- **M3 — 이벤트 구동 싱크.** push-after-write 디바운스, pull-on-request throttle + reindex,
  충돌 처리, 옵션. launchd 잡 폐기 + SETUP.md 갱신.

## 10. 테스트 전략

- 데몬 통합: 기동 → 엔드포인트 → 동시 읽기 → write→read 일관성.
- 다중 클라이언트 시뮬: N 프록시 → 1 데몬, 단일 그래프 적재·락 에러 0·write 직렬화 확인.
- 싱크: git clone 2개 샌드박스, 원격 push 모사 → pull-on-request + reindex, 충돌 시나리오.
- 라이프사이클: 자동 기동 레이스(동시 기동 → 1개 생존), idle 종료, 크래시 복구(데몬 kill → 프록시 재기동).
- 크로스플랫폼: Windows 실기 필요 항목 명시(§11).

## 11. 결정 사항 (확정 2026-06-25)

1. **포트 전략** — ✅ vault 경로 해시 기반 **결정적 포트 + portfile**.
2. **쓰기 폴백** — ✅ **(a) 명확한 에러로 거절**. → 데몬 기동 실패 시 쓰기는 수행하지 않음.
   덕분에 M2에서 snapshot/`_build_lock`/WAL/os.replace **코드를 전부 삭제**할 수 있다(구 경로 미보존).
3. **idle** — ✅ **기본 off(상시가동)**, 활성 시 `idle_timeout` **30분**.
4. **pull 시 reindex** — ✅ **첫 요청에서 동기 reindex**(stale면 pull→reindex 후 서빙). 추후 필요 시
   "stale 즉시 응답 + 백그라운드 reindex"로 개선.
5. **deps 승격** — ✅ fastapi/uvicorn/pydantic을 **필수**로(requirements 갱신).
6. **Windows 실기 검증** — ✅ **M1 끝**(detach 기동·폴백 read) 1차 + **M3**(git 인증/GCM) 2차.
