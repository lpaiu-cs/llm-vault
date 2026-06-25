# AGENTS.md — LLM 에이전트 운영 지침

> 이 저장소는 **LLM-native second brain**입니다. 사람과 LLM 에이전트가 함께 읽고
> 쓰는 출처 기반(source-grounded)·감사 가능(auditable) 장기 기억 런타임입니다.
> 모든 에이전트(Claude, Cursor, Antigravity 등)는 작업 전 이 문서를 먼저 읽으세요.

전체 멘탈 모델은 [[Second Brain Operating Model]], 세부 규칙은 `00_System/`의 정책
문서들을 기준으로 합니다. 본 문서는 그 정책들을 **에이전트 행동 규칙**으로 압축한 것입니다.

---

## 0. 핵심 전제: LLM은 틀릴 수 있다

이 시스템의 모든 규율은 **"LLM 출력은 기본적으로 환각일 수 있다"**([[Hallucination as Default]])는
전제 위에 설계되었습니다. 따라서 원본(raw source), 출처 인용(citation), 불확실성 표시,
모순 보존, 사람 검토 큐는 **선택이 아니라 필수**입니다.

확신이 없으면 단정하지 말고, 출처를 댈 수 없으면 검토 큐로 보내세요.

---

## 1. 계층별 권한 (Layer Permissions)

| 계층 | 경로 | 에이전트 권한 | 성격 |
|------|------|---------------|------|
| Inbox | `05_Inbox/` | 추가 가능 / 처리 후 이동 | 미가공 인입물 |
| **Raw** | `06_Raw/` | **읽기 전용 (이관 후 수정 금지)** | 불변 원본 = 진실의 원천 |
| MOC | `10_MOC/` | 갱신 가능 | 지도(Map of Content) |
| Concepts | `20_Concepts/` | 갱신 가능 | 내구성 개념 지식 |
| Projects | `30_Projects/` | 갱신 가능 | 활성 작업 대시보드 |
| Decisions | `40_Decisions/` | 추가 가능 / 기존 불변 | 중요 선택과 근거 |
| Summaries | `50_Source_Summaries/` | 갱신 가능 | 원본 압축 이해 |
| Questions | `60_Open_Questions/` | 갱신 가능 | 미해결 질문 |
| Contradictions | `70_Contradictions/` | 갱신 가능 | 모순·낡은 가정 |
| Reviews | `80_Reviews/` | 갱신 가능 | 사람 검증 큐 |
| Engine | `90_Engine/` | 코드 변경은 신중히 | 런타임·인덱스·MCP |

### 1.1 절대 규칙

1. **`06_Raw/`는 불변이다.** 이관(ingest)이 끝난 raw 파일은 절대 수정·삭제하지 않는다.
   오타조차 고치지 않는다. 원본은 증거이며, 증거를 고치면 감사 추적이 깨진다.
   해석이 바뀌면 raw가 아니라 `50_Source_Summaries/` 또는 `20_Concepts/`를 고친다.
2. 에이전트가 갱신해도 되는 것은 **해석 계층**뿐이다:
   `20_Concepts/`, `30_Projects/`, `40_Decisions/`(추가), `50_Source_Summaries/`,
   `60_Open_Questions/`, `70_Contradictions/`, `80_Reviews/`, `10_MOC/`.
3. `90_Engine/`의 코드(`indexer.py`, `retriever.py`, `mcp_server.py`)는 꼭 필요한
   경우에만, 영향 범위를 확인하고 수정한다. 임의 변경 금지.

---

## 2. 출처 인용 (Citations)

- **중요한 사실 주장은 출처 경로를 인용한다.** 인용은 `06_Raw/` 상대 경로 또는 외부 URL.
  - 예: `근거: [[Source Summary — 2026-06-18-claude-mcp-debug]]` 또는
    `(출처: 06_Raw/chats/2026-06-18-claude-mcp-debug.md)`.
- 출처가 없는 주장은 "에이전트의 추론"임을 명시하거나 `80_Reviews/`로 보낸다.
- 무엇이 source인지, source 인용 규칙은 [[Source Policy]]를 따른다.

---

## 3. 불확실성·모순·검토 라우팅

- **불확실하거나 의심스러운 출력 → `80_Reviews/`.**
  - 신뢰도 낮음 → `80_Reviews/Low Confidence Claims.md`
  - 환각 의심 → `80_Reviews/Possible Hallucinations.md`
  - 사람 판단 필요 → `80_Reviews/Needs Human Review.md`
- **상충하는 주장 → `70_Contradictions/`.** 매끄럽게 덮어쓰지 말고 충돌을 **보존**한다.
  이론 충돌은 `Theory Conflicts.md`, 출처 충돌은 `Source Conflicts.md`,
  낡은 가정은 `Stale Assumptions.md`.
- 카테고리·상태(status) 정의는 [[Review Policy]]를 따른다.

> 충돌을 발견하면 "둘 중 옳은 쪽으로 노트를 고치는" 것이 아니라,
> **양쪽을 다 기록**하고 검토 큐에 올리는 것이 기본 행동이다.

---

## 4. 의사결정 기록 (Decisions)

- **중요한 선택은 `40_Decisions/`에 결정 기록(decision record)으로 남긴다.**
  파일명: `YYYY-MM-DD-short-kebab-title.md` ([[Naming Convention]]).
- **기존 결정을 조용히 덮어쓰지 않는다.** 결정이 바뀌면:
  1. 새 결정 기록을 만든다.
  2. 새 기록에 `[[옛 결정]]`을 `replaces` 관계로 명시한다.
  3. 옛 기록의 frontmatter `status`를 `superseded`로 바꾸고, 본문 상단에
     `> 이 결정은 [[새 결정]]으로 대체됨` 배너를 추가한다(본문 내용 자체는 남긴다).

---

## 5. 노트 생성 절제 (Anti-Bloat)

- **모든 임시 생각을 concept node로 만들지 않는다.** `20_Concepts/`는 *내구성 있는*
  개념 지식만을 위한 곳이다. 일회성 메모는 `05_Inbox/notes/`나 프로젝트 대시보드의
  로그 섹션에 둔다.
- **중복 페이지를 만들지 말고 기존 페이지를 갱신한다.** 새로 만들기 전에
  `list_nodes()`(MCP) 또는 디렉터리 검색으로 기존 node를 먼저 확인한다.
  중복 후보가 의심되면 `80_Reviews/`에 `duplicate-concept-candidate`로 올린다.
- **프로젝트 페이지는 대시보드다.** 모든 세부사항을 쏟아붓지 말고, 정책·결정·개념·
  검토 항목으로 **링크**한다. 덤프가 아니라 현재 상태의 한눈 지도여야 한다.

---

## 6. 온톨로지 그래프 사용 (9-Predicate)

- predicate 엣지(`requires` · `utilizes` · `implemented_by` · `extends` · `abstracts` ·
  `causes` · `contradicts` · `replaces` · `defines`)는 **안정적 지식 그래프 관계**에만 쓴다.
- **raw source / inbox / 일시적 연관을 predicate 그래프에 강제로 넣지 않는다.**
  엣지는 내구성 있는 의미 관계를 위한 것이지 모든 연결을 위한 것이 아니다.
- 모호하면 엣지를 선언하지 않는다. ("불확실하면 비워라" — [[Ontology Specification]] §4)
- `05_Inbox/`, `06_Raw/`는 인덱서가 그래프 node로 만들지 않는다. `05_Inbox/`는 인덱싱
  완전 제외, `06_Raw/`는 전문검색 전용으로만 인덱싱된다(검색 가능·강등, edge 미파싱,
  wikilink/edge 타깃 아님 → 원본은 `source_path`로만 참조). 검색은 계층/신뢰도 인지로
  raw·낮은 신뢰도·검토 항목을 강등/제외한다 ([[2026-06-18-layer-and-confidence-aware-retrieval]]).

---

## 7. 인입 워크플로우 (요약)

1. 미가공물 → `05_Inbox/`
2. 안정적 원본 → `06_Raw/`로 이동/복사 (이후 불변)
3. `50_Source_Summaries/`에 source summary 작성 (`source_path`로 raw 인용)
4. 관련 `30_Projects/` 대시보드 갱신
5. 내구성 지식이면 `20_Concepts/` 갱신 (절제!)
6. 중요한 선택이 있으면 `40_Decisions/`에 결정 기록
7. 미해결 질문 → `60_Open_Questions/`
8. 충돌 → `70_Contradictions/`
9. 불확실·의심 출력 → `80_Reviews/`
10. 관련 MOC(`10_MOC/`) 갱신
11. 인덱싱/동기화 실행 또는 필요성 기록 (`90_Engine/`)

전체 절차와 주의사항은 [[Ingest Policy]]를 따른다.

---

## 8. 작성 형식 규칙

- 모든 Markdown은 Obsidian 호환을 유지한다.
- 내부 참조는 wikilink(`[[제목]]`), 증거 참조는 source 경로를 쓴다.
- 적절한 곳에 YAML frontmatter를 쓴다(예시는 [[Naming Convention]]).
- 근거 없는 사실 주장을 하지 않는다.
- 스크립트 변경이 필요한 작업은 코드에 `TODO`로 남긴다.

---

## 참고

- 운영 모델: [[Second Brain Operating Model]]
- 출처 정책: [[Source Policy]]
- 인입 정책: [[Ingest Policy]]
- 검토 정책: [[Review Policy]]
- 명명 규칙: [[Naming Convention]]
- 온톨로지 헌법: [[Ontology Specification]]
- 프로젝트 대시보드: [[LLM Second Brain]]
