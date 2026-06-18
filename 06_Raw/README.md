# 06_Raw — 불변 원본 (Immutable Source of Truth)

증거(evidence)로서의 원본을 원형에 가깝게 보존하는 곳입니다. **이관이 끝난 파일은
수정·삭제하지 않습니다.** 오타조차 고치지 않습니다 — 증거를 고치면 감사 추적이 깨집니다.
해석이 바뀌면 raw가 아니라 `50_Source_Summaries/` 또는 해석 계층을 고칩니다.

| 하위 폴더 | 용도 |
|-----------|------|
| `chats/` | 대화 원문 (`YYYY-MM-DD-topic.md`) |
| `papers/` | 논문 발췌/메타데이터 |
| `code-logs/` | 코드 diff, 에러 로그 |
| `screenshots/` | 이미지 + 캡션/OCR |
| `project-logs/` | 실험·실행·회의 로그 |
| `admin-records/` | 행정 기록 |

> 이 계층은 **전문검색 전용으로 인덱싱**됩니다. 즉 검색(BM25/임베딩)에는 잡히되
> 강등되고, **그래프 node는 아닙니다**(edge 미파싱, wikilink/edge 타깃 아님). raw는
> `source_path` 상대 경로로만 참조되며, 그래프상 대리물은 `50_Source_Summaries/`의
> source-summary node입니다. 규칙: [[Source Policy]], [AGENTS.md](../AGENTS.md) §1.1,
> 계층 정책: [[2026-06-18-layer-and-confidence-aware-retrieval]].
