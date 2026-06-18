#!/usr/bin/env bash
# scripts/test-template-allowlist.sh
# ─────────────────────────────────────────────────────────────
# template-allowlist 매칭 로직 단위 테스트. git/네트워크 불필요.
#   사용: scripts/test-template-allowlist.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALLOWLIST="$SCRIPT_DIR/template-allowlist.txt"
# shellcheck source=scripts/lib-allowlist.sh
. "$SCRIPT_DIR/lib-allowlist.sh"

pass=0
fail=0
check() { # <file> <expect: allow|block>
  local f="$1" want="$2" got
  if tmpl_allow_match "$f" "$ALLOWLIST"; then got=allow; else got=block; fi
  if [ "$got" = "$want" ]; then
    printf '  ok    %-55s %s\n' "$f" "$got"
    pass=$((pass + 1))
  else
    printf '  FAIL  %-55s want=%s got=%s\n' "$f" "$want" "$got"
    fail=$((fail + 1))
  fi
}

# 차단: 지식 계층의 실제 콘텐츠는 모두 public 금지(README/.gitkeep만 예외)
check "06_Raw/foo.md"                                  block
check "50_Source_Summaries/foo.md"                     block
check "05_Inbox/2026-06-18 note.md"                    block
check "30_Projects/private-project.md"                 block
check "30_Projects/LLM Second Brain.md"                block
check "40_Decisions/2026-07-01-personal-decision.md"   block
check "40_Decisions/2026-06-18-second-brain-architecture.md" block
check "20_Concepts/Tokenizer.md"                       block
check "10_MOC/Development MOC.md"                       block
check "60_Open_Questions/Implementation Questions.md"  block
check "70_Contradictions/foo.md"                       block
check "80_Reviews/foo.md"                              block

# 허용: 프레임워크 + 스켈레톤 구조 파일 + examples/mini-vault
check "90_Engine/retriever.py"                         allow
check "00_System/Retrieval Policy.yaml"                allow
check "06_Raw/README.md"                               allow
check "50_Source_Summaries/README.md"                  allow
check "20_Concepts/README.md"                          allow
check "20_Concepts/.gitkeep"                           allow
check "10_MOC/README.md"                               allow
check "examples/mini-vault/20_Concepts/Tokenizer.md"  allow
check "examples/mini-vault/README.md"                  allow
check "examples/mini-vault/eval_queries.json"          allow
check "README.md"                                      allow
check "scripts/sync-template.sh"                       allow

echo ""
echo "passed=$pass failed=$fail"
[ "$fail" -eq 0 ]
