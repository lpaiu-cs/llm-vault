---
id: moc_architecture
title: Architecture MOC
aliases:
  - 카파시 아키텍처 MOC
  - Architecture Hub
  - LLM OS Hub
type: Category-MOC
moc: "[[Karpathy LLM Framework MOC]]"
parent_moc: "[[Karpathy LLM Framework MOC]]"
child_nodes:
  - "[[LLM OS]]"
  - "[[Transformer]]"
  - "[[Context Window]]"
  - "[[Tokenizer]]"
  - "[[Byte Pair Encoding]]"
  - "[[Glitch Tokens]]"
tags:
  - AI/Architecture
  - PKM
  - Hub
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: a2b3c4d5-e6f7-4a8b-bcde-1234567890bc
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 2
related_nodes:
  - "[[Karpathy LLM Framework MOC]]"
  - "[[Implementation MOC]]"
---

> [!INFO] 카테고리 MOC 정체성
> 본 노트는 `[[Karpathy LLM Framework MOC]]` 산하의 **Architecture** 영역 진입 허브입니다. Karpathy가 대중에게 각인시킨 '원시 컴퓨팅 아키텍처로서의 LLM'이라는 개념과, 그 구조적 한계 및 구성 요소를 다루는 6개의 원자 노드를 군집화합니다.

## 1. 소속 원자 노드 및 관계망

| 노드 | 한 줄 정의 | 대표 엣지 |
|------|------------|-----------|
| `[[LLM OS]]` | LLM을 단순 텍스트 생성기가 아닌 하드웨어 제어 CPU로 보는 관점 | `requires [[Context Window]]` |
| `[[Transformer]]` | 현재 모든 LLM의 근간이 되는 신경망 백본 아키텍처 | `implemented_by [[nanoGPT]]` |
| `[[Context Window]]` | LLM OS의 RAM에 해당하는 자원이자 물리적 추론 공간 | `abstracts [[Memory-mapped IO]]` |
| `[[Tokenizer]]` | 문자열을 모델이 이해할 수 있는 토큰 가중치로 변환하는 서브프레임 | `implemented_by [[Byte Pair Encoding]]` |
| `[[Byte Pair Encoding]]` | 통계적 빈도 기반의 서브워드 분할 토크나이저 알고리즘 | `causes [[Glitch Tokens]]` |
| `[[Glitch Tokens]]` | 토크나이저의 정렬 실패로 인해 추론 붕괴를 유발하는 불량 토큰 | `requires [[Tokenizer]]` |

## 2. 아키텍처 레이어 흐름

```
[Transformer] ──implemented_by──> [nanoGPT]
      │
      ▼ requires
[LLM OS] ───requires───> [Context Window]
      │                       ▲
      ▼ abstracts             │ limits
[Tool Use]                    │
      ▲                       │
      │ utilized by           │
[Tokenizer] ──implemented_by──> [Byte Pair Encoding] ──causes──> [Glitch Tokens]
```

## Sources

- [Intro to Large Language Models — Karpathy](https://www.youtube.com/watch?v=zjkBMFhNj_g)
- [Let's build the GPT Tokenizer — Karpathy](https://www.youtube.com/watch?v=zduSFxRajkE)
