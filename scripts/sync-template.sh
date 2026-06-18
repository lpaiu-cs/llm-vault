#!/usr/bin/env bash
# scripts/sync-template.sh
# ─────────────────────────────────────────────────────────────
# 템플릿 전용 개선만 공개 레포(upstream)에 반영한다.
#
# 이 저장소의 워킹 카피는 origin=private(개인 second brain), upstream=public(템플릿)
# 구조다. 개인 데이터(05_Inbox/06_Raw/50_Source_Summaries 등)는 private에만 두고,
# 엔진/정책/문서 같은 템플릿 개선만 골라 공개 템플릿으로 올린다.
#
# 동작: upstream/main에서 분기한 임시 브랜치에 지정한 커밋만 cherry-pick → 개인
#       데이터 경로가 섞였는지 가드 검사 → 통과 시 upstream/main으로 push.
#
# 사용:
#   scripts/sync-template.sh <commit-ish> [<commit-ish> ...]
#   예) scripts/sync-template.sh 174e250            # 단일 커밋
#       scripts/sync-template.sh A^..B               # 범위
#
# 주의: 개인 데이터가 생긴 뒤에는 절대 `git push upstream main`을 직접 하지 말 것.
#       반드시 이 스크립트로 "템플릿 안전" 커밋만 선별해 올린다.
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: scripts/sync-template.sh <commit-ish> [<commit-ish> ...]" >&2
  exit 2
fi

# 개인 데이터 전용 경로(.gitkeep/README 같은 구조 파일은 예외로 허용)
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

# ── 가드: 개인 데이터 경로가 섞였는지 검사 ──
leak="$(git diff --name-only upstream/main.."$tmp_branch" \
        | grep -E "$PRIVATE_RE" | grep -vE "$ALLOW_RE" || true)"
if [ -n "$leak" ]; then
  echo "[ABORT] 개인 데이터 경로가 포함되어 공개 push를 중단합니다:" >&2
  echo "$leak" | sed 's/^/    /' >&2
  exit 1
fi

echo "[*] 변경 파일(공개될 내용):"
git diff --name-only upstream/main.."$tmp_branch" | sed 's/^/    /'

echo "[*] push → upstream/main"
git push upstream "$tmp_branch:main"
echo "[+] 공개 템플릿 동기화 완료."
