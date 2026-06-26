#!/usr/bin/env bash
# scripts/pull-framework.sh — private 인스턴스가 public 템플릿(upstream)의 '프레임워크'만
# 가져오는 공식 경로. sync-template.sh(private→public)의 정확한 역방향(public→private).
#
# 왜 전체 `git merge upstream/main`을 쓰지 않나:
#   public = 스켈레톤 + examples 데모, private = 실지식 누적 → 두 트리가 구조적으로 분기돼
#   있다. full merge는 (a) private 지식 파일을 modify/delete 충돌로 끌고 오고, (b)
#   examples/mini-vault 데모를 실볼트에 주입해 그래프를 오염시킨다. 그래서 merge가 아니라
#   '프레임워크 경로만' upstream/main에서 선택 체크아웃한다(지식 계층은 절대 건드리지 않음).
#
# 가져오는 것: 엔진(90_Engine)·문서(docs)·스크립트(scripts)·정책(00_System)·루트 문서·설정 예시.
# 의도적 제외: 지식 계층(10_MOC..80_Reviews, 05_Inbox, 06_Raw)·examples/(데모)·ltm_cache.db.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

if ! git remote | grep -qx upstream; then
  echo "[pull-framework] 'upstream' 리모트가 없습니다. 먼저 등록하세요:" >&2
  echo "  git remote add upstream https://github.com/lpaiu-cs/ltm-vault" >&2
  exit 1
fi

FRAMEWORK_PATHS=(
  90_Engine docs scripts 00_System
  requirements.txt .mcp.json.example AGENTS.md README.md SETUP.md
)

echo "[pull-framework] git fetch upstream ..."
git fetch upstream

echo "[pull-framework] checkout framework paths from upstream/main ..."
git checkout upstream/main -- "${FRAMEWORK_PATHS[@]}"

# checkout는 추가/수정만 반영한다. upstream에서 '삭제된' 프레임워크 파일도 맞춰 지운다
# (안 그러면 삭제된 cron/스크립트 등이 private에 유령처럼 남는다). 지식 계층은 경로 밖이라 무관.
echo "[pull-framework] reconciling deletions (upstream에서 사라진 프레임워크 파일 제거) ..."
git ls-files -- "${FRAMEWORK_PATHS[@]}" | while IFS= read -r f; do
  git cat-file -e "upstream/main:$f" 2>/dev/null || git rm -q --ignore-unmatch -- "$f"
done

if git diff --cached --quiet; then
  echo "[pull-framework] 변경 없음 — 프레임워크가 이미 최신입니다."
  exit 0
fi

echo "[pull-framework] 스테이징된 프레임워크 변경:"
git --no-pager diff --cached --stat

cat <<'NOTE'

[pull-framework] 지식 계층은 건드리지 않았습니다. 검토 후 커밋하세요:
  git diff --cached                          # 변경 확인
  git commit -m "chore: pull framework from upstream"
  git push
엔진 코드가 바뀌었으면 MCP 클라이언트를 재시작해야 새 동작/도구명이 적용됩니다.
NOTE
