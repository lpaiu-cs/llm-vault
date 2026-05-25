---
id: moc_philosophy
title: Philosophy MOC
aliases:
  - 카파시 철학 MOC
  - Karpathy Philosophy Hub
  - Paradigm MOC
type: Category-MOC
moc: "[[Karpathy LLM Framework MOC]]"
parent_moc: "[[Karpathy LLM Framework MOC]]"
child_nodes:
  - "[[Software 2.0]]"
  - "[[Software 3.0]]"
  - "[[Vibe Coding]]"
  - "[[The Bitter Lesson]]"
  - "[[Hallucination as Default]]"
tags:
  - AI/LLM
  - PKM
  - Philosophy
  - Paradigm
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: a1b2c3d4-e5f6-4789-abcd-1234567890ab
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 9
related_nodes:
  - "[[Karpathy LLM Framework MOC]]"
  - "[[Andrej Karpathy]]"
source_urls:
  - https://karpathy.medium.com/software-2-0-a64152b37c35
  - http://www.incompleteideas.net/IncIdeas/BitterLesson.html
---

> [!INFO] 카테고리 MOC 정체성
> 본 노트는 `[[Karpathy LLM Framework MOC]]`의 4대 하위 MOC 중 **Philosophy** 영역의 진입 허브입니다. Karpathy가 LLM·소프트웨어·AI 전반에 대해 견지하는 **패러다임 수준의 멘탈 모델**을 5개 원자 노드로 분리해 보관합니다. 기술 구현(`[[Implementation MOC]]`)이나 아키텍처(`[[Architecture MOC]]`)와 달리 본 영역은 "왜 그렇게 보는가"라는 **세계관 레이어**를 다룹니다.

---

## 1. 소속 원자 노드 및 관계망

| 노드 | 한 줄 정의 | 대표 엣지 |
|------|------------|-----------|
| `[[Software 2.0]]` | 데이터·손실함수·신경망 훈련으로 프로그램을 자동 탐색하는 패러다임 | `contradicts [[Software 1.0]]` |
| `[[Software 3.0]]` | 자연어 프롬프트·툴 라우팅·에이전트 루프로 소프트웨어를 가동하는 LLM 중심 패러다임 | `extends [[Software 2.0]]` |
| `[[Vibe Coding]]` | 자연어 의도(Intent)를 흐름으로 제시하면 AI가 구현·실행을 전담하는 개발 스타일 | `requires [[Software 3.0]]` |
| `[[The Bitter Lesson]]` | 인간 휴리스틱 주입은 장기적으로 범용 컴퓨테이션 확장 알고리즘을 이길 수 없다는 교훈 | `contradicts [[Rule-based AI]]` |
| `[[Hallucination as Default]]` | LLM은 끊임없이 환각하는 Dreaming Machine이라는 관점 | `requires [[Reflection Loop]]` |

---

## 2. 철학적 진화 흐름

```
[Software 1.0] ──contradicts──> [Software 2.0] ──extends──> [Software 3.0]
                                      │                          │
                                      │ defined by               │ enables
                                      ▼                          ▼
                            [The Bitter Lesson]            [Vibe Coding]
                                      │
                                      │ explains
                                      ▼
                          [Hallucination as Default]
                                      │
                                      │ requires
                                      ▼
                              [Reflection Loop]
```

세 가지 흐름이 본 MOC 내부에서 동시에 작동합니다.

1. **패러다임 진화 축**: Software 1.0 → 2.0 → 3.0
2. **정당화 축**: The Bitter Lesson이 2.0과 3.0의 근원적 근거
3. **실패 모드 축**: Vibe Coding과 LLM 일반이 Hallucination as Default를 유발하므로 Reflection Loop 필수

---

## 3. 노드 추가 기준

본 MOC에 신규 노드를 편입할 때는 다음 3조건을 충족해야 합니다.

1. **패러다임 레벨 추상화**여야 함 — 특정 알고리즘이나 라이브러리는 `[[Architecture MOC]]` 또는 `[[Implementation MOC]]`로 분류
2. Karpathy 본인의 발언·에세이·강연에서 **직접 인용 가능한 출처** 보유
3. 9개 술어 중 최소 1개로 본 MOC의 기존 노드와 연결 가능

---

## Sources

- [Software 2.0 — Karpathy Medium](https://karpathy.medium.com/software-2-0-a64152b37c35)
- [The Bitter Lesson — Rich Sutton](http://www.incompleteideas.net/IncIdeas/BitterLesson.html)
- [Andrej Karpathy — X/Twitter](https://x.com/karpathy)
