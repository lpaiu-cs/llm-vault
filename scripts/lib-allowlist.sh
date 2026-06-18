# scripts/lib-allowlist.sh
# ─────────────────────────────────────────────────────────────
# 템플릿 공개 허용 경로 매칭 라이브러리.
# sync-template.sh(실제 동기화)와 test-template-allowlist.sh(테스트)가 공용으로 쓴다.
# 단독 실행용이 아니라 `source` 되는 라이브러리다.

# 한 줄 패턴 정규화: 주석(#…) 제거 + 양끝 공백 제거(내부 공백은 보존: "LLM Second Brain.md").
_tmpl_norm() {
  local s="${1%%#*}"
  s="${s#"${s%%[![:space:]]*}"}"   # ltrim
  s="${s%"${s##*[![:space:]]}"}"   # rtrim
  printf '%s' "$s"
}

# tmpl_allow_match <file> <allowlist-file>
#   파일 경로가 allowlist의 한 패턴이라도 매칭되면 0(허용), 아니면 1(차단).
#   패턴 규칙:
#     - 끝이 '/' 이면 디렉터리 접두 매칭(하위 전체 허용)
#     - 그 외에는 정확 매칭(글롭 '*', '?' 사용 가능)
tmpl_allow_match() {
  local f="$1" allowlist="$2" line pat
  while IFS= read -r line || [ -n "$line" ]; do
    pat="$(_tmpl_norm "$line")"
    [ -z "$pat" ] && continue
    case "$pat" in
      */)
        case "$f" in "$pat"*) return 0 ;; esac
        ;;
      *)
        # shellcheck disable=SC2053  # 의도된 글롭 매칭(우변 비인용)
        [[ "$f" == $pat ]] && return 0
        ;;
    esac
  done < "$allowlist"
  return 1
}
