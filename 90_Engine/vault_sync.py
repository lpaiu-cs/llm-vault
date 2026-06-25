"""90_Engine/vault_sync.py — 데몬이 구동하는 git 동기화 헬퍼(이벤트 구동).

git은 서브프로세스 + 하드 타임아웃으로 격리하고, 요청 서빙 경로를 절대 블록하지 않게
호출부(vault_daemon)에서 스케줄한다. 충돌은 자동으로 해결하지 않고(rebase --abort) 상태로
표면화한다 — 사용자 데이터라 파괴적 자동 조치 금지. See docs/DAEMON_DESIGN.md §5.

git 환경은 `LC_ALL=C`(영어 메시지 고정 → 출력 분류 안정화) + `GIT_TERMINAL_PROMPT=0`
(자격증명 프롬프트로 매달리지 않게)로 고정한다.

각 함수는 (ok_or_changed: bool, status: str, detail: str)를 반환한다.
status ∈ {"ok","conflict","rejected","error"}.
"""
import os
import subprocess

_GIT_ENV = {**os.environ, "LC_ALL": "C", "LANG": "C", "GIT_TERMINAL_PROMPT": "0"}


def _git(vault_root, args, timeout):
    return subprocess.run(
        ["git", "-C", str(vault_root), *args],
        capture_output=True, text=True, timeout=timeout, env=_GIT_ENV,
    )


def is_git_repo(vault_root, timeout=10) -> bool:
    try:
        r = _git(vault_root, ["rev-parse", "--is-inside-work-tree"], timeout)
        return r.returncode == 0 and r.stdout.strip() == "true"
    except Exception:
        return False


def has_remote(vault_root, timeout=10) -> bool:
    try:
        r = _git(vault_root, ["remote"], timeout)
        return r.returncode == 0 and bool(r.stdout.strip())
    except Exception:
        return False


def _head(vault_root, timeout):
    r = _git(vault_root, ["rev-parse", "HEAD"], timeout)
    return r.stdout.strip() if r.returncode == 0 else None


def commit_local(vault_root, message, timeout=60):
    """add -A → commit(변경 없으면 'nothing to commit'을 ok로 처리). push는 하지 않는다.
    pull 전에 로컬을 먼저 commit해 두면 autostash 없이 rebase가 깔끔히 처리한다."""
    try:
        _git(vault_root, ["add", "-A"], timeout)
        c = _git(vault_root, ["commit", "-m", message], timeout)
        if c.returncode != 0 and "nothing to commit" not in (c.stdout + c.stderr).lower():
            return (False, "error", (c.stdout + c.stderr).strip()[-600:])
        return (True, "ok", "")
    except subprocess.TimeoutExpired:
        return (False, "error", f"git commit timeout ({timeout}s)")
    except Exception as e:  # noqa: BLE001
        return (False, "error", repr(e))


def pull(vault_root, timeout=60):
    """fetch + rebase. 호출 전 로컬 변경은 commit_local로 커밋돼 있어야 한다(autostash 미사용).
    HEAD가 바뀌면 changed=True. 충돌이면 rebase --abort로 원복하고 ("conflict")로 표면화한다."""
    try:
        before = _head(vault_root, timeout)
        r = _git(vault_root, ["pull", "--rebase"], timeout)
        if r.returncode != 0:
            out = (r.stdout + r.stderr)
            low = out.lower()
            # rebase가 실제로 진행 중인지(.git/rebase-*)로도 판별 — 로케일 무관
            mid_rebase = _git(vault_root, ["rev-parse", "--git-path", "rebase-merge"], timeout)
            in_rebase = (mid_rebase.returncode == 0
                         and os.path.isdir(os.path.join(str(vault_root), mid_rebase.stdout.strip())))
            if in_rebase or any(s in low for s in ("conflict", "could not apply")):
                _git(vault_root, ["rebase", "--abort"], timeout)
                return (False, "conflict", out.strip()[-600:])
            return (False, "error", out.strip()[-600:])
        after = _head(vault_root, timeout)
        return (before != after, "ok", "")
    except subprocess.TimeoutExpired:
        return (False, "error", f"git pull timeout ({timeout}s)")
    except Exception as e:  # noqa: BLE001
        return (False, "error", repr(e))


def commit_push(vault_root, message, timeout=60):
    """commit_local → push. push가 non-fast-forward로 거부되면 ("rejected")로 표면화
    (호출부가 pull-rebase 후 재시도한다)."""
    committed, status, detail = commit_local(vault_root, message, timeout)
    if status != "ok":
        return (False, status, detail)
    try:
        p = _git(vault_root, ["push"], timeout)
        if p.returncode != 0:
            out = (p.stdout + p.stderr)
            low = out.lower()
            if "rejected" in low or "non-fast-forward" in low or "fetch first" in low:
                return (False, "rejected", out.strip()[-600:])
            return (False, "error", out.strip()[-600:])
        return (True, "ok", "")
    except subprocess.TimeoutExpired:
        return (False, "error", f"git push timeout ({timeout}s)")
    except Exception as e:  # noqa: BLE001
        return (False, "error", repr(e))
