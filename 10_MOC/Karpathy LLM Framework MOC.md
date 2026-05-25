---
id: framework_karpathy_llm_v1
title: Karpathy LLM Framework MOC
aliases:
  - 카파시 프레임워크
  - Karpathy Frame
  - LLM Knowledge Root
type: Framework-Root-MOC
moc: self
parent_moc: null
child_moc:
  - "[[Philosophy MOC]]"
  - "[[Architecture MOC]]"
  - "[[Implementation MOC]]"
  - "[[Pedagogy MOC]]"
tags:
  - AI/LLM
  - PKM
  - Knowledge-Graph
  - Architecture
  - LTM
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: 7f3c4a8b-1d2e-4f5a-9c8b-3e2f1a7d6b9c
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 9
related_nodes:
  - "[[Andrej Karpathy]]"
  - "[[LLM OS]]"
  - "[[Software 2.0]]"
  - "[[Eureka Labs]]"
source_urls:
  - https://karpathy.ai
  - https://www.youtube.com/watch?v=zjkBMFhNj_g
  - https://github.com/karpathy/llm.c
  - https://github.com/karpathy/nanoGPT
---

> [!IMPORTANT] 문서 정체성
> 본 노트는 Andrej Karpathy의 공개 강의, 에세이, GitHub 레포지토리, Eureka Labs 행보에서 일관되게 추출되는 **LLM의 본질적 멘탈 모델**을 Obsidian 지식 그래프 및 향후 AI 에이전트의 **장기 메모리(LTM)**로 이식하기 위한 최상위 MOC(Map of Content)입니다. 4대 하위 MOC(`[[Philosophy MOC]]`, `[[Architecture MOC]]`, `[[Implementation MOC]]`, `[[Pedagogy MOC]]`)의 진입 허브 역할을 수행합니다.

> [!NOTE] v1.0 변경사항 요약
> - 사실 정확성: 토크나이저 결함 정량 수치 정성화, `[[llm.c]]` 사양을 순수 C/CUDA로 정밀화, `[[Eureka Labs]]`를 "Teacher + AI" 모델로 재정의
> - 누락 철학 노드 편입: `[[Software 2.0]]`, `[[Software 3.0]]`, `[[Vibe Coding]]`, `[[The Bitter Lesson]]`, `[[Hallucination as Default]]`
> - 온톨로지 강제 제약: 엣지 술어 9개로 고정, 4대 계층 MOC 정의
> - LTM 실전 아키텍처: 2단 하이브리드 검색, DuckDB 증분 캐싱(MD5 해시), 그래프 기반 Reflection 검증 루프

---

## 1. LLM 핵심 이론 및 원자적 노드

### 1.1 LLM의 본질적 멘탈 모델: Two Files

- `[[Parameters File]]`: 모델의 가중치($\theta$)가 들어있는 순수 데이터 구조체 (예: `llama3.bin`).
- `[[Run Code File]]`: 가중치를 읽어 순방향 전파(Forward Pass)를 구동하는 경량 인터프리터 (예: `run.c`).

### 1.2 Pre-training vs Fine-tuning

- `[[Base Model]]`: 인터넷 말뭉치를 압축하여 '다음 토큰을 예측'하는 통계적 최적화 모델.
- `[[Assistant Model]]`: `[[SFT]]`와 `[[RLHF]]`를 거쳐 지시 이행과 대화형 페르소나를 획득한 모델.

### 1.3 Tokenizer의 한계점

`[[Andrej Karpathy]]`는 글자(Character)와 토큰(Token)의 불일치를 다루는 `[[Byte Pair Encoding]]` 알고리즘이 LLM의 비직관적 결함의 근원이라고 지적합니다. 대표적 현상으로 문자 수 계산 오류(strawberry의 r 개수), 숫자 연산 취약성, 다국어 처리 효율 저하, 그리고 `[[Glitch Tokens]]` 유발이 있습니다.

### 1.4 System 1 vs System 2 추론

- `[[System 1 추론]]`: 고정된 계산 비용(Forward Pass)으로 즉각 토큰을 뱉어내는 직관적 연산. 현재 LLM의 기본 모드.
- `[[System 2 추론]]`: 토큰 생성 과정에서 스스로 교정·분기 탐색하며 글을 써 내려가는 의도적 연산. `[[Tree of Thoughts]]`, `[[MCTS]]`, `[[Reflection Loop]]`가 이 영역.

### 1.5 카파시 사상의 근본 철학 노드

- `[[Software 2.0]]`: 코드를 인간이 직접 작성하는 대신 데이터·목적 함수·신경망 훈련으로 프로그램을 자동 탐색하는 패러다임.
- `[[Software 3.0]]`: 가중치 훈련 단계를 넘어 자연어 프롬프트·툴 라우팅·에이전트 루프의 조합으로 소프트웨어를 가동하는 LLM 중심 연산 패러다임.
- `[[Vibe Coding]]`: 로우 레벨 문법·디버깅에 얽매이지 않고, 자연어 의도(Intent)를 흐름으로 제시하면 AI가 구현·실행을 전담하는 2025-2026년형 개발 스타일.
- `[[The Bitter Lesson]]`: 인간의 주관적 지식·휴리스틱 주입은 장기적으로 컴퓨터 하드웨어 확장(Computation Scaling)을 이용한 범용 알고리즘을 이길 수 없다는 Rich Sutton의 교훈.
- `[[Hallucination as Default]]`: "LLM은 끊임없이 환각하는 Dreaming Machine이며, 사실 발화는 프롬프트·데이터에 의해 정교하게 통제된 운 좋은 환각일 뿐"이라는 카파시의 관점.

---

## 2. GitHub 레포지토리 아키텍처 분석

### 2.1 minGPT & nanoGPT

PyTorch 최신 API를 활용해 `[[Transformer]]` 아키텍처의 핵심을 수백 줄의 가독성 높은 코드로 압축. 후기 nanoGPT에서 혼합 정밀도(`[[AMP]]`), `[[FlashAttention]]`, `[[torch.compile]]`을 순차 결합하여 파이토치 생태계 내 성능 한계를 시험.

### 2.2 llm.c

거대 프레임워크인 PyTorch를 배제하고, **순수 C와 CUDA**만으로 GPT-2/3의 훈련 및 인퍼런스 커널을 바닥부터 구현. 컴파일 오버헤드를 극단적으로 낮추고 `[[Memory-mapped IO]]`를 통해 원시 데이터 가동 효율을 극대화. 에이전트 루프의 엣지 런타임 경량화 가능성을 시사.

---

## 3. 최신 기술 스택 및 에이전트 지견 (2026)

### 3.1 Eureka Labs와 AI 네이티브 교육

"Teacher + AI" 모델: 인간 교사는 핵심 고품질 콘텐츠와 커리큘럼 아키텍처를 설계하고, AI 에이전트는 학생 개개인의 이해도·언어·진도에 맞게 이를 개별화하여 전달·가이드하는 구조. 교육용 PKM 역시 정적 텍스트가 아닌 **개인화 가이드** 형태를 띠어야 함을 방증.

### 3.2 LLM OS (Large Language Model Operating System)

```
       [ 사용자 / 애플리케이션 ]
                 │
                 ▼
┌────────────────────────────────────────┐
│               LLM OS                   │
│  (컨텍스트 윈도우 = RAM / 추론 엔진 = CPU)  │
└──────────────────┬─────────────────────┘
                   │
      ┌────────────┼────────────┐
      ▼            ▼            ▼
 ┌─────────┐  ┌─────────┐  ┌─────────┐
 │ 파일시스템│  │ 주변기기 │  │인터넷/API│
 │  (RAG)  │  │(코드실행)│  │ (브라우징)│
 └─────────┘  └─────────┘  └─────────┘
```

- `[[Context Window]]`: 컴퓨터의 RAM. 제한된 윈도우 자원을 효율적으로 관리하기 위한 하이브리드 캐싱·페이지 교체 전략 필요.
- `[[Tool Use]]`: 코드 인터프리터, 웹 브라우저, 로컬 파일 시스템 등 주변장치(Peripherals) 제어 인터페이스.

---

## 4. Graphify 온톨로지 제약 및 4단 MOC 구조

### 4.1 엄격히 제한된 엣지 술어 (Core Predicates × 9)

지식 그래프의 무질서한 팽창을 막고 RDF/Property Graph 변환 일관성을 유지하기 위해 온톨로지 술어를 9개로 강제 제한합니다.

| # | Predicate | 의미 | 사용 예시 |
|---|-----------|------|-----------|
| 1 | `defines` | A가 B의 개념을 정의함 | `[[Intro to LLMs]] defines [[Parameters File]]` |
| 2 | `causes` | A가 원인이 되어 B를 유발함 | `[[Byte Pair Encoding]] causes [[Glitch Tokens]]` |
| 3 | `utilizes` | A가 기능 수행을 위해 B를 도구로 씀 (B 없이도 A 존재 가능) | `[[LLM OS]] utilizes [[Tool Use]]` |
| 4 | `implemented_by` | A 이론이 B 실체로 구현됨 | `[[Transformer]] implemented_by [[nanoGPT]]` |
| 5 | `replaces` | A가 기존 B 스택을 대체함 | `[[llm.c]] replaces [[PyTorch]]` |
| 6 | `requires` | A가 존재·작동하기 위해 B가 필수 전제 (B 없으면 A 없음) | `[[LLM OS]] requires [[Context Window]]` |
| 7 | `extends` | A가 B의 개념을 상위 확장함 | `[[Software 3.0]] extends [[Software 2.0]]` |
| 8 | `contradicts` | A가 B의 철학과 정면 대치됨 | `[[The Bitter Lesson]] contradicts [[Rule-based AI]]` |
| 9 | `abstracts` | A가 B의 복잡 구조를 고차원으로 추상화 | `[[LLM OS]] abstracts [[Tool Use]]` |

### 4.2 4대 계층 MOC 아키텍처

```
┌────────────────────────────────────────────────────────┐
│         [[Karpathy LLM Framework MOC]] (THIS NODE)     │
└───────┬──────────────┬────────────────┬──────────────┬─┘
        │              │                │              │
        ▼              ▼                ▼              ▼
┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐
│ Philosophy   ││ Architecture ││Implementation││   Pedagogy   │
│    MOC       ││    MOC       ││     MOC      ││     MOC      │
│(Software 2.0)││  (LLM OS)    ││  (nanoGPT)   ││(Eureka Labs) │
└──────────────┘└──────────────┘└──────────────┘└──────────────┘
```

---

## 5. AI 에이전트 LTM 엔지니어링 설계 (Deep Dive)

### 5.1 2단 하이브리드 검색 파이프라인

그래프 워크 단독 검색은 사용자가 정확한 노드 키워드를 제시하지 않을 때(예: "왜 LLM은 strawberry의 r 개수를 못 세지?") 진입점 노드를 찾지 못해 실패합니다.

```
[사용자 쿼리]
     │
     ▼
1차: 하이브리드 검색 (Dense Embedding + Sparse BM25)
     │
     ▼
Seed Node 식별: [[Tokenizer]] / [[Byte Pair Encoding]]
     │
     ▼
2차: Graph k-hop Expansion (최적 맥락 서브그래프 추출)
     │
     ▼
컨텍스트 윈도우(RAM)에 서브그래프 적재
```

Microsoft GraphRAG, HippoRAG, LightRAG의 공통 아키텍처를 차용한 구조입니다.

### 5.2 노드 임베딩 캐싱: DuckDB 스키마

보관소가 2,000노트 이상으로 확장될 시 매 쿼리마다 마크다운 전체를 파싱하는 것은 불가능합니다. 변경된 노드만 점진적(Incremental)으로 재임베딩하기 위해 MD5 해시 추적 기반의 로컬 캐시 백엔드를 둡니다.

```sql
-- 90_Engine/ltm_cache.db (DuckDB)

CREATE TABLE nodes (
    node_id        UUID PRIMARY KEY,
    file_path      VARCHAR NOT NULL UNIQUE,
    title          VARCHAR NOT NULL,
    aliases        VARCHAR[],
    type           VARCHAR,                  -- Concept / MOC / Framework-Root
    moc            VARCHAR,                  -- parent MOC link
    md5_hash       VARCHAR NOT NULL,         -- 본문 변경 추적
    embedding      FLOAT[1536],              -- OpenAI / BGE / E5 등
    embedding_hash VARCHAR,
    last_indexed   TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE edges (
    edge_id      UUID PRIMARY KEY,
    source_id    UUID REFERENCES nodes(node_id),
    target_id    UUID REFERENCES nodes(node_id),
    predicate    VARCHAR NOT NULL CHECK (
        predicate IN (
            'defines','causes','utilizes','implemented_by',
            'replaces','requires','extends','contradicts','abstracts'
        )
    ),
    weight       FLOAT DEFAULT 1.0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_edges_source    ON edges(source_id);
CREATE INDEX idx_edges_target    ON edges(target_id);
CREATE INDEX idx_edges_predicate ON edges(predicate);
```

CHECK 제약으로 4.1의 9개 술어를 DB 레벨에서 강제하여 무분별한 술어 확장을 원천 차단합니다.

### 5.3 그래프 기반 System 2 검증 루프 (Reflection)

에이전트가 답변을 생성할 때 `[[Hallucination as Default]]`를 억제하기 위해, 생성 결과를 그래프 온톨로지와 역으로 대조 검증합니다.

```
[답변 생성]
     │
     ▼
생성 문장 내 주요 엔티티 추출 (NER)
     │
     ▼
지식 그래프 내 존재 여부 스캔 (NetworkX / DuckDB JOIN)
     │
     ├─[존재함 & 관계 일관] ──> [최종 출력]
     │
     └─[부재 / 관계 모순] ──> Hallucination 판정
                                    │
                                    ▼
                  올바른 맥락 경로를 컨텍스트에 강제 주입
                                    │
                                    ▼
                              [재추론 루프]
```

핵심 동작 원리는 답변 스트림에서 고유 명사나 핵심 기술 스택을 엔티티로 추출한 뒤, 해당 엔티티들이 Vault 내부 그래프에 실제 노드로 존재하는지, 그리고 정의된 엣지 관계(예: `replaces`, `causes`)와 모순되지 않는지 NetworkX 스캔으로 검증하는 것입니다.

---

## 6. Vault 디렉터리 아키텍처 및 파일명 4대원칙

### 6.1 권장 디렉터리 구조 (최대 2단)

```
Vault Root/
│
├── 00_System/                  # 에이전트 템플릿 및 온톨로지 정의
│   ├── Template_Atomic.md
│   └── Ontology Specification.md
│
├── 10_MOC/                     # 4대 계층 MOC Hub
│   ├── Karpathy LLM Framework MOC.md   ← 본 노트
│   ├── Philosophy MOC.md
│   ├── Architecture MOC.md
│   ├── Implementation MOC.md
│   └── Pedagogy MOC.md
│
├── 20_Concepts/                # 원자적 지식 노드 (대부분의 파일)
│   ├── Software 2.0.md
│   ├── Byte Pair Encoding.md
│   ├── System 2 추론.md
│   └── ...
│
└── 90_Engine/                  # LTM 머신 전용 (Git Ignore 권장)
    ├── ltm_cache.db
    └── node_embeddings.json
```

### 6.2 파일명 4대원칙

1. **명사형 단일 엔티티 원칙**: 파일명은 지식 그래프의 노드 ID(PK). 접두사(번호·날짜)를 배제하고 개념을 나타내는 지배적 명사를 그대로 사용. `[[`자동완성 시 휴먼 프릭션 최소화.
2. **Case & Space Normalization**: 영문은 PascalCase 또는 Title Case 엄격 준수. 약어와 풀네임 중 하나를 메인으로 고정, 나머지는 Frontmatter `aliases`로 이전. DB 파싱 시 Case-sensitive 파편화 방지.
3. **특수문자 전면 배제 (Sanitization)**: 알파벳·숫자·공백·언더바·하이픈만 허용. `/`, `:`, `[`, `]`, `(`, `)` 금지. Git 동기화 및 SQLite/DuckDB 인덱싱 안정성 확보.
4. **MOC 접미사 분리**: MOC 노트는 파일명 뒤에 한 칸 띄우고 ` MOC` 접미사 부착 (`Software 2.0 MOC.md`). 원자적 노트와 시각적·구조적 격리.

---

## 7. 활용 워크플로우

```
[1단계: Raw Ingestion] ──> [2단계: Atomic Graphing] ──> [3단계: Agentic Synthesis]
카파시 강의/코드 덤프       개념어 추출 & [[링크]] 연결       MOC 노드 생성 및 그래프 쿼리
```

1. **원자적 노트화**: 하나의 노트에는 하나의 개념만. 본문은 3문장 이내 정의 + 코드 조각으로 밀도 극대화.
2. **의도적 엣지 생성**: 9개 술어 중 하나를 명시적으로 선택하여 링크. "이 개념은 어떤 버그를 유발하는가(`causes`)?", "어떤 아키텍처의 상위 확장인가(`extends`)?"
3. **MOC 중심 유지**: 4대 MOC를 그래프의 중력 중심으로 두고 모든 원자 노트가 최소 1개 MOC에 `requires` 또는 `defines` 엣지로 연결되도록 강제.

---

## 8. 다음 작업 (Backlog)

- [ ] `[[Philosophy MOC]]` 생성 → `[[Software 2.0]]`, `[[Software 3.0]]`, `[[Vibe Coding]]`, `[[The Bitter Lesson]]`, `[[Hallucination as Default]]` 원자 노트 5개 분리
- [ ] `[[Architecture MOC]]` 생성 → `[[LLM OS]]`, `[[Transformer]]`, `[[Context Window]]`, `[[Tokenizer]]`, `[[Byte Pair Encoding]]`, `[[Glitch Tokens]]` 원자 노트 분리
- [ ] `[[Implementation MOC]]` 생성 → `[[nanoGPT]]`, `[[minGPT]]`, `[[llm.c]]`, `[[FlashAttention]]`, `[[Memory-mapped IO]]` 원자 노트 분리
- [ ] `[[Pedagogy MOC]]` 생성 → `[[Eureka Labs]]`, `[[Intro to LLMs]]`, `[[Teacher and AI Model]]` 원자 노트 분리
- [ ] `00_System/Ontology Specification.md` 작성 — 9개 술어 정의·사용 규칙·금지 사례 명문화
- [ ] `90_Engine/` DuckDB 캐시 초기화 스크립트 (Python) 작성
- [ ] NetworkX 기반 Reflection 검증 루프 프로토타입 작성

---

## Sources

- [Andrej Karpathy — Personal Site](https://karpathy.ai)
- [Intro to Large Language Models — YouTube](https://www.youtube.com/watch?v=zjkBMFhNj_g)
- [llm.c — GitHub](https://github.com/karpathy/llm.c)
- [nanoGPT — GitHub](https://github.com/karpathy/nanoGPT)
- [Let's build the GPT Tokenizer — YouTube](https://www.youtube.com/watch?v=zduSFxRajkE)
- [Software 2.0 — Medium Essay](https://karpathy.medium.com/software-2-0-a64152b37c35)
- [Eureka Labs](https://eurekalabs.ai)
- [The Bitter Lesson — Rich Sutton](http://www.incompleteideas.net/IncIdeas/BitterLesson.html)
