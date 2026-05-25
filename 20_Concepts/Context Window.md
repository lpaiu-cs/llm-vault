---
id: concept_context_window
title: Context Window
aliases:
  - 컨텍스트 윈도우
  - 맥락 창
  - LLM RAM
type: Concept
moc: "[[Architecture MOC]]"
parent_moc: "[[Architecture MOC]]"
tags:
  - AI/Architecture
  - Memory
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: d5e6f7a8-b9c0-4d1e-ef0f-4567890123ef
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 2
related_nodes:
  - "[[LLM OS]]"
  - "[[Memory-mapped IO]]"
  - "[[System 2 추론]]"
---

# Context Window

LLM이 단일 추론 단계(Forward Pass)에서 한 번에 인입하여 유지하고 사유할 수 있는 최대 토큰의 물리적 한계 범위. 아키텍처적으로 컴퓨터의 작동 메모리인 RAM에 정밀하게 대응된다. 2025-2026년 기준 수백만 토큰 수준으로 확장되었으나, 윈도우 크기가 증가할수록 Attention 연산 비용이 제곱(O(N^2))으로 폭증하는 한계를 지닌다.

## 핵심 메커니즘

1. Attention Bottleneck: 모든 토큰이 서로를 참조해야 하므로 메모리 적재 용량과 계산 복잡도가 창의 크기에 비례해 증가
2. Context Compression: 긴 맥락 속에서 중요한 핵심 엔티티 정보만을 남기고 불필요한 토큰 가중치를 요약/교체하는 기법 요구됨
3. Needle in a Haystack (NIAH): 대규모 창 내부 깊숙한 곳에 숨겨진 특정 사실 정보를 정확히 리트리벌해내는 모델의 성능 척도

## 핵심 엣지

- `[[LLM OS]] requires [[Context Window]]` — 운영체제 런타임의 사유 면적이자 메모리 공간으로서 필수 요구됨
- `[[Context Window]] requires [[FlashAttention]]` — 제곱 스케일로 폭증하는 attention 연산 병목을 IO-aware 커널로 제어해 주지 않으면 물리적 대용량 윈도우 가동 불가

(v1.0.2 리팩토링: 약한 결합이었던 `abstracts [[Memory-mapped IO]]` 엣지는 제거됨. mmap 관련 결합은 [[Memory-mapped IO]] 측에서 `[[Context Window]] requires [[Memory-mapped IO]]`로 단일 진실로 관리.)

## PKM 시사점

컨텍스트 윈도우는 유한한 자원이다. 따라서 에이전트 LTM 가동 시 무조건 전체 노드를 때려 넣는 방식은 불가능하다. 인덱서 스크립트를 통해 사전에 고도로 압축된 1~2 hop 내외의 서브그래프 관계성 구조 정보만을 추출하여 윈도우에 적재하는 하이브리드 전략이 요구된다.

## Sources

- [Intro to Large Language Models — Karpathy](https://www.youtube.com/watch?v=zjkBMFhNj_g)
