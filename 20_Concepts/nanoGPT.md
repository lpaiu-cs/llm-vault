---
id: concept_nanogpt
title: nanoGPT
aliases:
  - 나노GPT
  - Optimized PyTorch GPT
type: Concept
moc: "[[Implementation MOC]]"
parent_moc: "[[Implementation MOC]]"
tags:
  - AI/Implementation
  - Optimization
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: c5d6e7f8-a9b0-4123-cdef-4567890123ef
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 3
related_nodes:
  - "[[minGPT]]"
  - "[[FlashAttention]]"
  - "[[llm.c]]"
---

# nanoGPT

minGPT의 교육적 한계를 넘어서, **순수 PyTorch 환경에서 대규모 모델 훈련 가속화를 달성하기 위해 빌드된 고도로 최적화된 레포지토리**. 가독성을 크게 해치지 않으면서도 최신 NVIDIA GPU 하드웨어 하이퍼 스펙을 온전히 쥐어짜낼 수 있는 컴파일 및 연산 기법들이 대거 집약되어 있다.

## 핵심 메커니즘

1. **torch.compile**: 파이토치 2.0 커널 융합(Kernel Fusion)을 가동하여 런타임 연산 그래프 오버헤드를 제로화
2. **혼합 정밀도 훈련(AMP)**: `bfloat16`과 `float32` 가중치 연산을 동적으로 결합하여 메모리 대역폭 점유를 절반으로 억제
3. **커널 레벨 어텐션 가속**: 수동으로 행렬을 쪼개 연산하는 대신 하드웨어 최적화 커널인 `[[FlashAttention]]`을 내장 호출

## 핵심 엣지

- `[[nanoGPT]] extends [[minGPT]]` — 가독 모델인 minGPT 아키텍처 레이어를 하드웨어 최적화 관점에서 직접 상위 확장함
- `[[nanoGPT]] utilizes [[FlashAttention]]` — 어텐션 가중치 병목을 돌파하기 위해 최적화된 연산 하드웨어 커널을 도구로 활용함
- `[[llm.c]] replaces [[nanoGPT]]` — 파이썬 런타임과 PyTorch 프레임워크 자체의 종속성을 완전히 깨부수기 위한 C/CUDA 단독 엔진으로 기능적 교체가 일어남

## PKM 시사점

nanoGPT는 지식 베이스의 **"운영 최적화 단계"** 에 대응된다. 원자 노드가 누적되면, 매번 풀 스캔하는 오버헤드를 막기 위해 `--force` 플래그 및 MD5 해시 테이블 캐싱과 같은 런타임 최적화 프로토콜(indexer.py v1.0.1)을 덧붙여 연산 효율을 높여야 한다.

## Sources

- [Karpathy GitHub - nanoGPT 공식 레포지토리](https://github.com/karpathy/nanoGPT)
