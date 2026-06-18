#!/usr/bin/env bash
# scripts/sync-template.sh
# ─────────────────────────────────────────────────────────────
# 템플릿 전용 개선만 공개 레포(upstream)에 반영한다.
#
# 이 저장소의 워킹 카피는 origin=private(개인 second brain), upstream=public(템플릿)
# 구조다. 개인 데이터는 private에만 두고, 엔진/정책/문서 같은 템플릿 개선만 골라
# 공개 템플릿으로 올린다.
#
# 가드(2단계, "기본 차단, 명시적 허용"):
#   1) allowlist  — 변경 파일이 scripts/template-allowlist.txt 의 패턴에 하나도
#                   매칭되지 않으면 중단한다. 개인 데이터가 30_Projects/40_Decisions/
#                   60/70/80 등 어느 계층에 들어가든 실수로 공개되지 않게 막는 1차 방어.
#   2) denylist   — 05_Inbox/06_Raw/50_Source_Summaries 콘텐츠는 명시적으로 재차 차단
#                   (allowlist 사고를 대비한 보조 방어).
#
# 동작: upstream/main에서 분기한 임시 브랜치에 지정한 커밋만 cherry-pick → 가드 검사
#       → 통과 시 upstream/main으로 push.
#
# 사용:
#   scripts/sync-template.sh [--dry-run] <commit-ish> [<commit-ish> ...]
#   예) scripts/sync-template.sh 174e250            # 단일 커밋
#       scripts/sync-template.sh --dry-run A^..B    # push 없이 가드만 검사
#
# 주의: 개인 데이터가 생긴 뒤에는 절대 `git push upstream main`을 직접 하지 말 것.
#       반드시 이 스크립트로 "템플릿 안전" 커밋만 선별해 올린다.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALLOWLIST="$SCRIPT_DIR/template-allowlist.txt"
# shellcheck source=scripts/lib-allowlist.sh
. "$SCRIPT_DIR/lib-allowlist.sh"

DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=1
  shift
fi

if [ "$#" -lt 1 ]; then
  echo "usage: scripts/sync-template.sh [--dry-run] <commit-ish> [<commit-ish> ...]" >&2
  exit 2
fi

if [ ! -f "$ALLOWLIST" ]; then
  echo "[ABORT] allowlist 파일이 없습니다: $ALLOWLIST" >&2
  exit 1
fi

# 보조 denylist: 개인 데이터 전용 경로(.gitkeep/README 같은 구조 파일은 예외)
PRIVATE_RE='^(05_Inbox/|06_Raw/|50_Source_Summaries/)'
ALLOW_RE='(\.gitkeep|/README\.md)$'

orig_branch="$(git rev-parse --abbrev-ref HEAD)"
tmp_branch="_template_sync_$$"

cleanup() {
  git cherry-pick --abort >/dev/null 2>&1 || true
  git checkout -q "$orig_branch" 2>/dev/null || true
  git branch -D "$tmp_branch" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[*] fetch upstream..."
git fetch -q upstream

echo "[*] create $tmp_branch from upstream/main"
git checkout -q -b "$tmp_branch" upstream/main

echo "[*] cherry-pick: $*"
for c in "$@"; do
  git cherry-pick "$c"
done

# ── 변경 파일 분류: allowed / blocked, 그리고 보조 denylist 적중 ──
allowed=()
blocked=()
leak=()
while IFS= read -r f; do
  [ -z "$f" ] && continue
  if printf '%s\n' "$f" | grep -qE "$PRIVATE_RE" && ! printf '%s\n' "$f" | grep -qE "$ALLOW_RE"; then
    leak+=("$f")
  fi
  if tmpl_allow_match "$f" "$ALLOWLIST"; then
    allowed+=("$f")
  else
    blocked+=("$f")
  fi
done < <(git diff --name-only upstream/main.."$tmp_branch")

if [ "${#allowed[@]}" -eq 0 ] && [ "${#blocked[@]}" -eq 0 ]; then
  echo "[!] upstream/main 대비 변경이 없습니다. 올릴 내용이 없어 종료합니다."
  exit 0
fi

# ── 보조 denylist 가드 ──
if [ "${#leak[@]}" -gt 0 ]; then
  echo "[ABORT] 개인 데이터 경로(05/06/50)가 포함되어 공개 push를 중단합니다:" >&2
  printf '    %s\n' "${leak[@]}" >&2
  exit 1
fi

# ── allowlist 가드 ──
if [ "${#blocked[@]}" -gt 0 ]; then
  echo "[ABORT] allowlist에 없는 경로가 있어 공개 push를 중단합니다(기본 차단):" >&2
  printf '    %s\n' "${blocked[@]}" >&2
  echo "" >&2
  echo "    → 정말 공개해도 되는 파일이면 scripts/template-allowlist.txt 에 추가하고," >&2
  echo "      개인 데이터면 해당 커밋을 동기화 대상에서 제외하세요." >&2
  exit 1
fi

echo ""
echo "[+] 공개될 파일(${#allowed[@]}개):"
printf '    %s\n' "${allowed[@]}"

if [ "$DRY_RUN" -eq 1 ]; then
  echo ""
  echo "[dry-run] 가드 통과. push는 생략합니다."
  exit 0
fi

echo ""
echo "[*] push → upstream/main"
git push upstream "$tmp_branch:main"
echo "[+] 공개 템플릿 동기화 완료."
