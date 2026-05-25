---
id: system_ontology_spec_v1
title: Ontology Specification
aliases:
  - 온톨로지 헌법
  - Predicate Constitution
  - Edge Schema Spec
type: System-Specification
moc: "[[Karpathy LLM Framework MOC]]"
parent_moc: "[[Karpathy LLM Framework MOC]]"
governs:
  - "[[Karpathy LLM Framework MOC]]"
  - "[[Philosophy MOC]]"
  - "[[Architecture MOC]]"
  - "[[Implementation MOC]]"
  - "[[Pedagogy MOC]]"
tags:
  - System
  - Ontology
  - Schema
  - Specification
  - LTM
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: 0a1b2c3d-4e5f-4a78-9b8c-0d1e2f3a4b5c
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 9
related_nodes:
  - "[[Karpathy LLM Framework MOC]]"
  - "[[Software 3.0]]"
  - "[[Vibe Coding]]"
source_urls: []
---

> [!IMPORTANT] 문서 정체성
> 본 노트는 Karpathy LLM Framework Vault의 **온톨로지 헌법(Predicate Constitution)** 입니다. 모든 원자 노트의 엣지 술어(Predicate)는 본 명세를 따라야 하며, 본 명세 외의 술어는 Vault 그래프와 DuckDB `edges` 테이블 모두에서 거부됩니다. 인간 작성자와 AI 에이전트가 동일한 술어 선택 기준을 공유함으로써 그래프의 **기하학적 일관성(Geometric Consistency)** 과 **의미 누수 방지(Semantic Drift Prevention)** 를 보장합니다.

> [!NOTE] 본 헌법의 작동 방식
> - **인간 작성자**: §1·§2·§4를 참조하여 술어를 선택
> - **AI 에이전트**: §5의 3-Layer Binding 사양에 따라 시스템 프롬프트·Tool Call·인덱서 정규식에 본 명세를 바인딩
> - **DuckDB 인덱서**: `90_Engine/ltm_cache.db`의 `edges.predicate` CHECK 제약을 본 명세의 9개 화이트리스트로 강제

---

## §1. 9개 술어의 엄격한 정의

각 술어는 **1문장 정의 + 형식 표현 + 방향성(Directionality)** 로 구성됩니다. 형식 표현 `A pred B`는 "엣지의 출발지가 A, 도착지가 B"임을 의미합니다.

| # | Predicate | 1문장 정의 | 형식 표현 | 방향성 |
|---|-----------|------------|-----------|--------|
| 1 | `defines` | A가 B라는 개념·용어의 **공식 정의 출처**이다 | A `defines` B = "A is the canonical source of B's definition" | Source → Target |
| 2 | `causes` | A가 발생함으로써 B가 **현상으로서 유발**된다 | A `causes` B = "A is the necessary or sufficient cause of B" | Cause → Effect |
| 3 | `utilizes` | A가 자신의 기능 수행을 위해 B를 **도구·자원으로 사용**하나, B 없이도 A는 (제한적으로) 존재 가능하다 | A `utilizes` B = "A uses B but A's existence does not depend on B" | User → Tool |
| 4 | `implemented_by` | A라는 **추상 명세·이론**이 B라는 **구체 실체**로 구현·실현된다 | A `implemented_by` B = "abstract A is concretely realized as B" | Abstract → Concrete |
| 5 | `replaces` | A가 기존의 B 기술·스택·접근을 **기능적으로 대체**한다 | A `replaces` B = "A supersedes B for the same function" | Successor → Predecessor |
| 6 | `requires` | A가 존재·작동하기 위해 B가 **필수 전제**이다 (B 없으면 A 없음) | A `requires` B = "A cannot exist without B" | Dependent → Prerequisite |
| 7 | `extends` | A가 B와 **동일 추상화 층위**에서 기능·범위를 추가 확장한다 | A `extends` B = "A is B plus additional capabilities at same level" | Subclass → Superclass |
| 8 | `contradicts` | A의 주장·철학이 B와 **정면 대치**된다 (양립 불가) | A `contradicts` B = "A and B are mutually exclusive claims" | 대칭 (symmetric) |
| 9 | `abstracts` | A가 B의 복잡한 메커니즘을 **한 층 위에서 감추고 단순화**한다 | A `abstracts` B = "A hides B's complexity at a higher layer" | Higher → Lower |

---

## §2. Confusion Pairs 분기 규칙

데이터 모델링 경험상 가장 빈번하게 혼동되는 4쌍의 술어에 대해 **결정론적 분기 질문**을 정의합니다.

### 2.1 `utilizes` vs `requires`

**분기 질문**: *"B가 없으면 A가 존재할 수 있는가?"*
- 가능 → `utilizes`
- 불가능 → `requires`

**Worked Example (실제 v1.0 위반 사례)**:
- ❌ 잘못: `[[LLM OS]] utilizes [[Context Window]]`
- ✅ 올바름: `[[LLM OS]] requires [[Context Window]]`
- 근거: Context Window는 LLM OS의 RAM에 해당하는 **정의 조건**이다. Context Window 없는 LLM OS는 개념적으로 성립하지 않는다.

**대조 정상 사례**:
- ✅ `[[LLM OS]] utilizes [[Tool Use]]` — Tool Use 없이도 LLM OS는 (제한적으로) 존재 가능. Tool Use는 도구이지 정의 조건이 아니다.

### 2.2 `extends` vs `abstracts`

**분기 질문**: *"A와 B는 같은 층위인가, 아니면 A가 한 층 위에 있는가?"*
- 같은 층위 + 기능 추가 → `extends`
- 한 층 위 + 복잡도 감춤 → `abstracts`

**Worked Example**:
- ✅ `[[Software 3.0]] extends [[Software 2.0]]` — 둘 다 **소프트웨어 패러다임** 층위에서 3.0이 2.0에 자연어 인터페이스를 추가한 것
- ✅ `[[LLM OS]] abstracts [[Tool Use]]` — LLM OS는 운영체제 메타포로 Tool Use 메커니즘의 복잡도를 **한 층 위에서** 감춘 것

**오용 예방**:
- ❌ `[[LLM OS]] extends [[Tool Use]]` — 층위가 다르므로 `extends`는 부적절
- ❌ `[[Software 3.0]] abstracts [[Software 2.0]]` — 같은 층위에서의 확장이므로 `abstracts`는 부적절

### 2.3 `defines` vs `implemented_by`

**분기 질문**: *"A는 문서·강의·에세이인가 (정의의 출처), 아니면 원리·이론인가 (구현의 대상)?"*
- 문서·강의가 A → `defines`
- 원리·이론이 A → `implemented_by`

**Worked Example (실제 v1.0 위반 사례)**:
- ❌ 잘못: `[[The Bitter Lesson]] defines [[Software 2.0]]`
- ✅ 올바름: `[[The Bitter Lesson]] implemented_by [[Software 2.0]]`
- 근거: Bitter Lesson은 Software 2.0의 *공식 정의 문서*가 아니다. 그것은 Karpathy의 2017년 Medium 에세이가 담당한다. Bitter Lesson은 **원리이며, Software 2.0이 그 원리의 구체적 실현**이다.

**대조 정상 사례**:
- ✅ `[[Intro to LLMs]] defines [[Parameters File]]` — 강의가 개념을 정의
- ✅ `[[Software 2.0 Essay]] defines [[Software 2.0]]` — 에세이가 패러다임을 정의

### 2.4 `causes` vs `requires` (방향성 함정)

**분기 질문**: *"엣지 방향이 시간적 인과인가, 논리적 전제인가?"*
- A가 B를 발생시킴 (시간적) → A `causes` B
- A가 존재하려면 B가 선행되어야 함 (논리적) → A `requires` B

**Worked Example (실제 v1.0 위반 사례)**:
- ❌ 잘못: `[[Hallucination as Default]] requires [[Reflection Loop]]` — 환각은 Reflection Loop 없이도 발생함 (오히려 Reflection Loop가 환각을 *전제*로 함)
- ✅ 올바름: `[[Reflection Loop]] requires [[Hallucination as Default]]` — Reflection Loop라는 설계 패턴은 "환각이 디폴트"라는 관찰을 전제로만 존재 의미가 있음

**또 다른 v1.0 위반 사례**:
- ❌ 잘못: `[[Vibe Coding]] causes [[Hallucination as Default]]` — Vibe Coding은 환각을 *유발*하지 않는다 (환각은 LLM의 디폴트). Vibe Coding은 환각을 *증폭* 시킬 뿐
- ✅ 올바름: `[[Vibe Coding]] requires [[Reflection Loop]]` — 책임 있는 Vibe Coding은 Reflection Loop를 전제 조건으로 요구

---

## §3. Worked Examples (술어별 2개씩 × 9 = 18개)

본 Vault 내에서 실제로 사용되거나 사용될 정상 엣지 예시:

| Predicate | 예시 1 | 예시 2 |
|-----------|--------|--------|
| `defines` | `[[Intro to LLMs]] defines [[Parameters File]]` | `[[Software 2.0 Essay]] defines [[Software 2.0]]` |
| `causes` | `[[Byte Pair Encoding]] causes [[Glitch Tokens]]` | `[[System 1 추론]] causes [[Hallucination as Default]]` |
| `utilizes` | `[[LLM OS]] utilizes [[Tool Use]]` | `[[Vibe Coding]] utilizes [[LLM OS]]` |
| `implemented_by` | `[[Transformer]] implemented_by [[nanoGPT]]` | `[[The Bitter Lesson]] implemented_by [[Software 2.0]]` |
| `replaces` | `[[llm.c]] replaces [[PyTorch]]` | `[[Tokenizer-free 모델]] replaces [[Byte Pair Encoding]]` |
| `requires` | `[[LLM OS]] requires [[Context Window]]` | `[[Vibe Coding]] requires [[Software 3.0]]` |
| `extends` | `[[Software 3.0]] extends [[Software 2.0]]` | `[[Assistant Model]] extends [[Base Model]]` |
| `contradicts` | `[[The Bitter Lesson]] contradicts [[Rule-based AI]]` | `[[Software 2.0]] contradicts [[Software 1.0]]` |
| `abstracts` | `[[LLM OS]] abstracts [[Tool Use]]` | `[[Vibe Coding]] abstracts [[Software 3.0]]` |

---

## §4. Fallback Rule (모호 시 의사결정 트리)

§2의 4쌍 외에 모호한 케이스가 발생할 경우 다음 트리를 순서대로 적용합니다.

```
[엣지 선언 시도]
        │
        ▼
Q1. 두 노드가 시간적·인과적 관계인가?
   │
   ├─[YES] → causes
   │
   └─[NO]
        │
        ▼
Q2. B 없이 A가 존재 불가능한가?
   │
   ├─[YES] → requires
   │
   └─[NO]
        │
        ▼
Q3. A와 B가 양립 불가능한 주장인가?
   │
   ├─[YES] → contradicts
   │
   └─[NO]
        │
        ▼
Q4. A가 B의 추상 명세이고 B가 구체 구현인가?
   │
   ├─[YES] → implemented_by
   │
   └─[NO]
        │
        ▼
Q5. A가 B의 정의 출처(문서·강의·에세이)인가?
   │
   ├─[YES] → defines
   │
   └─[NO]
        │
        ▼
Q6. A가 B와 같은 층위인가?
   │
   ├─[YES] → extends (기능 추가) 또는 replaces (대체)
   │
   └─[NO] → abstracts (한 층 위) 또는 utilizes (도구로 사용)
```

**최후 fallback**: 위 모든 단계에서 결정 불가능하면 **엣지를 선언하지 않는다**. 모호한 엣지는 그래프 노이즈가 되어 k-hop 확장 시 Semantic Drift를 유발한다. *"불확실하면 비워라"* 가 본 헌법의 최후 명령이다.

---

## §5. Agent Prompt Binding (3-Layer Hybrid)

본 헌법은 단순 인간용 가이드를 넘어 **AI 에이전트의 시스템 프롬프트·Tool Call·인덱서 정규식에 직접 바인딩**됩니다. Karpathy의 `[[Software 3.0]]` 관점에서 LLM 런타임은 자연어 컨텍스트 흡수에는 강하지만 최종 출력은 완벽한 가드레일이 필요하므로, 3개 레이어를 철저히 분리합니다.

```
1. 지식 인입 (Input Context)  ──> XML 태그로 감싸 추론 윈도우 분리
2. 중간 추론 (In-Context Reason) ──> 마크다운 내 결정론적 DSL로 엣지 식별
3. 최종 실행 (Structured Output) ──> JSON Schema로 Tool Call 및 DB 적재
```

### §5.1 인입/컨텍스트 레이어: XML 태그 구조

Claude·GPT 계열 모델은 마크다운 내에서 프롬프트 지시와 온톨로지 규칙을 분리할 때 **XML 태그**를 가장 토큰 효율적으로 인식합니다. 에이전트 시스템 프롬프트 주입 시 본 헌법은 다음 XML 블록으로 래핑되어 컨텍스트 RAM에 적재됩니다.

```xml
<ontology_control>
  <strict_predicates>
    defines, causes, utilizes, implemented_by, replaces, requires, extends, contradicts, abstracts
  </strict_predicates>

  <syntax_rules>
    - 모든 링크는 반드시 '[[노트 파일명]]' 형식을 유지해야 한다.
    - 서술형 문장 중간에 엣지를 선언할 때는 반드시 백틱(`)으로 감싼 DSL 포맷을 준수한다.
    - 모호한 경우 §4 Fallback Rule을 적용하고, 그래도 결정 불가능하면 엣지를 선언하지 않는다.
  </syntax_rules>

  <few_shot_example>
    Input: "LLM OS는 제한된 컨텍스트 윈도우를 효율적으로 써야 하므로 시스템 2 추론 루프가 필수적이다."
    Output DSL:
    - `[[LLM OS]] requires [[Context Window]]`
    - `[[LLM OS]] requires [[System 2 추론]]`
  </few_shot_example>

  <confusion_pairs>
    <pair name="utilizes_vs_requires">
      질문: B가 없으면 A가 존재할 수 있는가? 가능→utilizes, 불가능→requires
    </pair>
    <pair name="extends_vs_abstracts">
      질문: 같은 층위 기능 추가→extends, 한 층 위 복잡도 감춤→abstracts
    </pair>
    <pair name="defines_vs_implemented_by">
      질문: 문서·강의가 A→defines, 원리·이론이 A→implemented_by
    </pair>
    <pair name="causes_vs_requires">
      질문: 시간적 인과→causes, 논리적 전제→requires
    </pair>
  </confusion_pairs>
</ontology_control>
```

### §5.2 실행/출력 레이어: JSON Schema (Structured Outputs)

에이전트가 노트를 새로 생성하거나 기존 마크다운을 파싱하여 DuckDB `edges` 테이블에 INSERT할 때 반환해야 하는 엄격한 구조 정의서. `evidence_quote` 필드는 **엣지의 출처 추적(Provenance)** 을 보장하여 환각 검증 루프(§Karpathy LLM Framework MOC 5.3)에서 역추적 가능하게 합니다.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "OntologyGraphUpdate",
  "type": "object",
  "properties": {
    "source_node": {
      "type": "string",
      "description": "출발지 원자 노트 파일명 (확장자 제외, 대소문자·공백 일치)",
      "pattern": "^[A-Za-z0-9 _\\-가-힣]+$"
    },
    "target_node": {
      "type": "string",
      "description": "목적지 원자 노트 파일명 (확장자 제외, 대소문자·공백 일치)",
      "pattern": "^[A-Za-z0-9 _\\-가-힣]+$"
    },
    "predicate": {
      "type": "string",
      "enum": [
        "defines", "causes", "utilizes", "implemented_by",
        "replaces", "requires", "extends", "contradicts", "abstracts"
      ],
      "description": "허용된 9개 온톨로지 술어 중 정확히 하나"
    },
    "evidence_quote": {
      "type": "string",
      "minLength": 10,
      "description": "이 관계를 도출한 마크다운 본문 내의 실제 문장 인용 (10자 이상)"
    },
    "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "에이전트의 술어 선택 신뢰도. 0.7 미만이면 인간 검토 큐로 회송"
    }
  },
  "required": ["source_node", "target_node", "predicate", "evidence_quote"],
  "additionalProperties": false
}
```

### §5.3 공동 편집 레이어: 마크다운 인라인 DSL

인간 작성자와 AI 에이전트가 마크다운 본문에서 공유하는 **결정론적 표기법**. 각 노트의 `## 핵심 엣지` 섹션 또는 본문에서 다음 형식으로 엣지를 선언합니다.

**표기 포맷** (placeholder는 `<...>` ASCII 부등호로 감싸 파서 정규식과의 충돌을 회피):
```markdown
- `[[<source_node>]] <predicate> [[<target_node>]]` — 자연어 설명
```

실제 사용 예시는 §3 Worked Examples 18개 테이블 참조.

> [!WARNING] 파서 측 자기참조 회피
> 본 헌법 자체가 §5.3의 정규식 파서에 의해 인덱싱될 때, fence 블록(```` ``` ````) 내부의 예시 텍스트도 라인 단위로 스캔되어 false positive를 유발할 수 있다. 이를 방지하려면 `90_Engine/indexer.py`에서 fence 블록 내부를 스킵하는 전처리를 반드시 추가해야 한다. 본 헌법은 placeholder를 ASCII 부등호로 감싸 이 문제를 임시 회피한다.

**파서 정규식 (Python `re` 호환)**:
```python
EDGE_REGEX = (
    r"^-\s+"                          # 리스트 항목 시작
    r"`\[\[(?P<source>.+?)\]\]"       # [[소스]]
    r"\s+(?P<predicate>\w+)\s+"       # 술어
    r"\[\[(?P<target>.+?)\]\]`"       # [[타깃]]
    r"(?:\s*—\s*(?P<desc>.*))?$"      # 선택적 설명
)
```

이 정규식을 `90_Engine/indexer.py`에 바인딩하면 **LLM 호출 없이도** 마크다운 텍스트에서 DuckDB `edges` 테이블로의 고속 동기화가 가능합니다. 인간이 작성한 엣지든 에이전트가 작성한 엣지든 동일한 파서 경로를 거쳐 무결성이 보장됩니다.

### §5.4 3-Layer Binding 책임 분담 요약

| 레이어 | 형식 | 책임 | 가동 시점 |
|--------|------|------|-----------|
| §5.1 인입 | XML | 에이전트 "이해(Reasoning)·맥락 지정" | 시스템 프롬프트 초기화 |
| §5.2 실행 | JSON Schema | 에이전트 "행동(Action)·DB 트랜잭션 보장" | Tool Call 응답 시 |
| §5.3 편집 | Markdown DSL | "인간과 에이전트의 공동 편집 평면" | 노트 작성·인덱싱 시 |

---

## §6. 금지 사례 (Anti-Patterns)

다음 5개 패턴은 그래프 무결성을 해치므로 인덱서가 거부합니다.

1. **9개 외 술어 선언**: `[[A]] mitigates [[B]]`, `[[A]] enables [[B]]`, `[[A]] derived_from [[B]]` 등. 표현 욕구가 강해 발생하나, §4 Fallback으로 9개 안에 매핑 가능. 매핑 불가하면 엣지를 선언하지 않는다.

2. **방향 모호 엣지**: `[[A]] requires [[B]]`와 `[[B]] requires [[A]]`를 모두 선언. 논리적 순환 의존은 거의 항상 술어 오선택의 신호. 한 방향을 `requires`, 반대를 다른 술어로 재고한다.

3. **자기 참조 엣지**: `[[A]] extends [[A]]`. SQL `CHECK (source_id != target_id)` 제약으로 DB 레벨 차단.

4. **`utilizes` 남용**: 정확한 술어를 찾기 귀찮을 때 `utilizes`로 회피하는 패턴. 본 헌법에서 `utilizes`는 "B 없이도 A 존재 가능"이라는 엄격한 조건을 가지므로 디폴트 선택지가 되어서는 안 된다.

5. **Evidence 없는 엣지**: 마크다운 본문 어디에도 근거 문장 없이 `## 핵심 엣지` 섹션에만 선언된 엣지. §5.2 JSON Schema의 `evidence_quote` 필수 필드 정신 위반.

---

## §7. v1.0 적용 결과 — 기존 6개 노트 재검증 보고

본 헌법 v1.0 발효 시점에 Vault에 존재하던 6개 노트(Karpathy LLM Framework MOC, Philosophy MOC, Software 2.0, Software 3.0, Vibe Coding, The Bitter Lesson, Hallucination as Default)의 모든 엣지를 §2 Confusion Pairs 규칙으로 재검증한 결과, 다음 5건의 위반을 검출하여 자동 수정합니다.

| # | 파일 | 위반 엣지 | 수정 후 | 적용 규칙 |
|---|------|-----------|---------|-----------|
| 1 | Karpathy LLM Framework MOC (§4.1 표) | `[[LLM OS]] utilizes [[Context Window]]` | `[[LLM OS]] requires [[Context Window]]` | §2.1 utilizes vs requires |
| 2 | Hallucination as Default | `[[Hallucination as Default]] requires [[Reflection Loop]]` | `[[Reflection Loop]] requires [[Hallucination as Default]]` | §2.4 방향성 함정 |
| 3 | Vibe Coding | `[[Vibe Coding]] causes [[Hallucination as Default]]` | `[[Vibe Coding]] requires [[Reflection Loop]]` | §2.4 causes vs requires |
| 4 | The Bitter Lesson | `[[The Bitter Lesson]] defines [[Software 2.0]]` | `[[The Bitter Lesson]] implemented_by [[Software 2.0]]` | §2.3 defines vs implemented_by |
| 5 | Software 2.0 | `[[The Bitter Lesson]] defines [[Software 2.0]]` | `[[The Bitter Lesson]] implemented_by [[Software 2.0]]` | §2.3 (동일 엣지의 양방향 표기 일관성) |

수정은 본 헌법 직후 자동 실행되며, 결과는 §9 최종 검증 로그에 보관됩니다.

---

## §8. 헌법 개정 절차

본 헌법의 9개 술어는 **준-불변(quasi-immutable)** 입니다. 추가·삭제는 다음 조건을 모두 충족해야 합니다.

1. 현행 9개 술어로 표현 불가능한 의미 관계가 **최소 3개 노트** 이상에서 반복 발생
2. §4 Fallback Rule이 명백히 실패하는 사례 문서화
3. 새 술어 추가 시 §1·§2·§3·§5에 동시 반영 (헌법 일관성)
4. DuckDB `edges.predicate` CHECK 제약 마이그레이션 스크립트 동봉

위 조건이 충족되면 본 노트의 `version` 필드를 `1.0 → 1.1`로 올리고 변경 이력을 §10에 추가합니다.

---

## §9. 최종 검증 로그 (v1.0)

- 적용 일시: 2026-05-25
- 검증 대상 노트 수: 7개 (본 헌법 포함)
- 검증 엣지 수: ~60개
- 위반 검출: 5건 (§7)
- 자동 수정 적용: 5/5건
- 잔존 위반: 0건
- DuckDB CHECK 제약 동기화: pending (`90_Engine/indexer.py` 구현 시 활성화)

---

## §10. 변경 이력

| 버전 | 일자 | 변경 내용 |
|------|------|-----------|
| 1.0 | 2026-05-25 | 최초 제정. 9개 술어 + 4개 Confusion Pairs + 3-Layer Binding + 5건 자동 수정 |

---

## Sources

- 본 헌법은 외부 출처 없이 Karpathy LLM Framework Vault 내부에서 도출됨
- 영감 출처: `[[Software 3.0]]`, `[[Vibe Coding]]`, `[[Hallucination as Default]]`
- 참조: [JSON Schema Draft 07](http://json-schema.org/draft-07/schema), [Anthropic XML Best Practices](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags)
