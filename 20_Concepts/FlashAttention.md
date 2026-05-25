---
id: concept_flash_attention
title: FlashAttention
aliases:
  - 플래시어텐션
  - GPU Memory-bound Optimization
type: Concept
moc: "[[Implementation MOC]]"
parent_moc: "[[Implementation MOC]]"
tags:
  - AI/Implementation
  - GPU
  - Hardware
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: e7f8a9b0-c1d2-4345-efab-6789012345fb
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 2
related_nodes:
  - "[[Context Window]]"
  - "[[nanoGPT]]"
  - "[[llm.c]]"
---

# FlashAttention

Dao 등이 제안한 **GPU 메모리 계층 구조(HBM ↔ SRAM)의 대역폭 한계를 돌파하기 위해 설계된 IO-Aware 고속 어텐션 연산 알고리즘**. 수학적 결과값은 일반 고정 Softmax Attention과 완전히 동일하지만, GPU 내부의 고속 캐시 메모리(SRAM) 블록 단위를 고려한 타일링(Tiling) 및 온라인 소프트맥스 연산을 통해 메모리 읽기/쓰기 횟수를 극단적으로 단축시켰다.

## 핵심 메커니즘

1. **타일링(Tiling)**: 거대한 어텐션 행렬 전체를 통째로 고대역폭 메모리(HBM)에 올리지 않고, GPU 내부 연산 코어 옆의 초고속 SRAM 캐시 크기에 맞게 블록 단위로 쪼개어 연산 유도
2. **온라인 소프트맥스(Online Softmax)**: 행렬을 쪼개 연산할 때 중간 결과물 합산 시 소프트맥스 분모 분자 가중치를 동적으로 스케일링 복원하는 수학적 기법을 도입하여 행렬 재로딩 오버헤드 원천 제거
3. **재연산(Recomputation)**: 역전파(Backward Pass) 시 대용량 정방형 어텐션 체크포인트 행렬을 메모리에 저장해 두는 대신, 필요할 때 SRAM 내부에서 고속으로 포워드 패스를 재연산하여 메모리 점유 공간을 선형($O(N)$)으로 제어

## 핵심 엣지

- `[[Context Window]] requires [[FlashAttention]]` — 제곱 스케일로 폭증하는 연산 병목을 하드웨어 IO 레벨에서 제어해 주지 않으면 물리적 대용량 맥락 창 가동이 불가능함
- `[[nanoGPT]] utilizes [[FlashAttention]]` — PyTorch 단독 추론/훈련 병목을 타파하기 위해 하드웨어 가속 플래시어텐션 모듈을 도구로 장착함

## PKM 시사점

FlashAttention은 메모리 계층 구조 간의 **"IO 병목 돌파"** 패러다임이다. 로컬 디스크(마크다운 파일)에서 지식을 꺼내 LLM의 사유 공간(Context RAM)으로 올리는 과정도 IO 병목을 유발한다. 전체 지식을 무차별적으로 로딩하는 대신, 인덱서가 구축한 고밀도 엣지 데이터만을 선별 적재하는 것은 지식 관리 환경에서의 FlashAttention 타일링 기법이라 볼 수 있다.

## Sources

- [Dao et al. (2022) — FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness](https://arxiv.org/abs/2205.14135)
