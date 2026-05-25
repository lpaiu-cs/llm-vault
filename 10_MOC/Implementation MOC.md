---
id: moc_implementation
title: Implementation MOC
aliases:
  - 카파시 구현 MOC
  - Implementation Hub
  - Code Core Hub
type: Category-MOC
moc: "[[Karpathy LLM Framework MOC]]"
parent_moc: "[[Karpathy LLM Framework MOC]]"
child_nodes:
  - "[[minGPT]]"
  - "[[nanoGPT]]"
  - "[[llm.c]]"
  - "[[FlashAttention]]"
  - "[[Memory-mapped IO]]"
tags:
  - AI/Implementation
  - PKM
  - Hub
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: a3b4c5d6-e7f8-4901-bcde-2345678901cd
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 2
related_nodes:
  - "[[Karpathy LLM Framework MOC]]"
  - "[[Architecture MOC]]"
---

> [!INFO] 카테고리 MOC 정체성
> 본 노트는 `[[Karpathy LLM Framework MOC]]` 산하의 **Implementation(구현)** 영역 진입 허브입니다. Andrej Karpathy의 "추상화의 장막에 숨지 말고 바닥부터(From Scratch) 코드를 짜라"는 교육 철학이 투영된 핵심 GitHub 레포지토리 아키텍처와, 가속 연산 하드웨어 최적화 기법을 다루는 5개의 원자 노드를 군집화합니다.

## 1. 소속 원자 노드 및 관계망

| 노드 | 한 줄 정의 | 대표 엣지 |
|------|------------|-----------|
| `[[minGPT]]` | 트랜스포머 아키텍처를 최소한의 코드로 구현한 교육용 PyTorch 레포지토리 | `Transformer implemented_by minGPT` |
| `[[nanoGPT]]` | minGPT를 진화시켜 프로덕션급 훈련 가속을 달성한 PyTorch 최적화 레포지토리 | `extends [[minGPT]]` |
| `[[llm.c]]` | 거대 프레임워크를 완전히 배제하고 순수 C/CUDA로 작성한 초경량 GPT 훈련 엔진 | `replaces [[PyTorch]]` |
| `[[FlashAttention]]` | GPU 메모리 계층 구조를 활용해 Attention 연산 속도를 혁신한 하드웨어 커널 | `abstracts [[SRAM-HBM IO]]` |
| `[[Memory-mapped IO]]` | OS 커널의 페이지 캐시를 활용해 대용량 데이터셋을 초고속 로딩하는 IO 기법 | `utilizes [[Page Cache]]` |

## 2. 구현 및 최적화 레이어 흐름

```
[Transformer]
     │
     ├─implemented_by─> [minGPT] ──extends─> [nanoGPT] ──utilizes─> [FlashAttention]
     │                                            │
     └─implemented_by─> [llm.c] ───replaces───────┘
                            │
                            └─utilizes─> [Memory-mapped IO]
```

## Sources

- [Andrej Karpathy GitHub 공식 레포지토리](https://github.com/karpathy)
