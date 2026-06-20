#!/usr/bin/env bash
# scripts/sync.sh
# ─────────────────────────────────────────────────────────────
# 개인 클라우드용 1-커맨드 동기화: 자동 커밋 → pull(rebase) → push.
# 기기 간(PC↔laptop) vault를 git만으로 옮기되, 매번 커밋 메시지를 쓰지 않아도
# 되도록 메시지를 자동 생성한다(타임스탬프 + 호스트명).
#
# ⚠️ 이 스크립트는 origin(=private 인스턴스)에만 push한다. 절대 upstream(public
#    템플릿)으로 보내지 않는다. 공개 템플릿 반영은 반드시 scripts/sync-template.sh
#    (allowlist 가드)로만 한다.
#
# 안전 동작:
#   - 먼저 로컬 변경을 전부 커밋(git add -A; .gitignore가 DB/.venv/.mcp.json 제외)
#   - pull --rebase 로 원격 변경 위에 내 커밋을 얹는다
#   - rebase 충돌 시 자동 해결하지 않고 중단·복구하고 알린다(데이터 안전 우선)
#   - 변경이 없으면 커밋을 건너뛴다(빈 커밋 안 만듦)
#
# 사용:
#   scripts/sync.sh                 # 자동 메시지로 동기화
#   scripts/sync.sh "메모 한 줄"     # 메시지를 직접 주고 싶을 때(선택)
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

REMOTE="origin"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"

if [ "$BRANCH" = "HEAD" ]; then
  echo "[ABORT] detached HEAD 상태입니다. 브랜치를 체크아웃한 뒤 다시 실행하세요." >&2
  exit 1
fi

HOST="$(hostname -s 2>/dev/null || hostname)"
STAMP="$(date '+%Y-%m-%d %H:%M:%S')"
MSG="${1:-sync: ${STAMP} (${HOST})}"

# 1) 로컬 변경 커밋 (없으면 건너뜀)
git add -A
if git diff --cached --quiet; then
  echo "[=] 커밋할 로컬 변경 없음."
else
  git commit -q -m "$MSG"
  echo "[+] committed: $MSG"
fi

# 2) 원격 변경을 rebase로 통합 (내 커밋을 원격 위에 재배치)
echo "[*] pull --rebase $REMOTE $BRANCH"
if ! git pull --rebase --autostash "$REMOTE" "$BRANCH"; then
  echo "" >&2
  echo "[ABORT] rebase 충돌이 발생했습니다. 자동 해결하지 않습니다." >&2
  echo "        충돌을 수동으로 해결(git status 확인 → 편집 → git add → git rebase --continue)" >&2
  echo "        하거나, 되돌리려면 git rebase --abort 후 다시 시도하세요." >&2
  exit 1
fi

# 3) 원격으로 push (origin 전용)
echo "[*] push $REMOTE $BRANCH"
git push -q "$REMOTE" "$BRANCH"
echo "[✓] synced → ${REMOTE}/${BRANCH}"
