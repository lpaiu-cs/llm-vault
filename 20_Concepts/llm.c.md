---
id: concept_llm_c
title: llm.c
aliases:
  - 엘엘엠점씨
  - Pure C CUDA GPT
type: Concept
moc: "[[Implementation MOC]]"
parent_moc: "[[Implementation MOC]]"
tags:
  - AI/Implementation
  - C
  - CUDA
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: d6e7f8a9-b0c1-4234-defa-5678901234fa
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 4
related_nodes:
  - "[[nanoGPT]]"
  - "[[Memory-mapped IO]]"
  - "[[Transformer]]"
---

# llm.c

PyTorch나 무거운 C++ 프레임워크 등 모던 거대 생태계를 전면 배제하고, **오직 순수 C와 CUDA만으로 GPT-2 및 GPT-3의 훈련/인퍼런스 코어 커널을 바닥부터 구현한 초경량 고속 신경망 엔진**. 컴파일 오버헤드가 단 몇 초에 불과하며, 단일 파일 수준의 소스 코드로 슈퍼컴퓨터급 가중치 스케일링 훈련을 가동하는 카파시의 장인정신 철학이 집대성된 레포지토리이다.

## 핵심 메커니즘

1. **수동 포워드/백워드 레이어 매핑**: 추상화된 미분 엔진(Autograd) 없이, 멀티헤드 어텐션, 레이어 정규화(LayerNorm), GELU 연산의 포워드 패스와 가중치 그래디언트 역전파 수학식을 직접 C 포인터 제어로 구현
2. **메모리 할당 통제**: 훈련 시작 시 일정한 단일 대용량 메모리 블록을 통째로 할당(Slab Allocation)한 뒤 내부에서 포인터 오프셋으로 잘라 사용하여 런타임 메모리 단편화 및 할당 지연 오버헤드를 제로화
3. **PyTorch 가중치 호환**: 빌드된 `.bin` 파일 포맷을 통해 PyTorch에서 사전 훈련된 가중치 파라미터를 유실 없이 다이렉트로 로딩 및 인퍼런스 가동

## 핵심 엣지

- `[[Transformer]] implemented_by [[llm.c]]` — 트랜스포머 레이어 가중치 연산 공식이 순수 C 및 CUDA 하드웨어 원시 기계어로 직접 체현됨
- `[[llm.c]] replaces [[PyTorch]]` — 복잡하고 무거운 파이썬 프레임워크 종속성을 완전히 걷어내고 컴파일러 단독 가동 레이어로 대체함
- `[[llm.c]] utilizes [[Memory-mapped IO]]` — 기가바이트급 말뭉치 데이터를 메모리 누수 없이 디스크에서 메모리로 초고속 인입하기 위해 mmap 커널 시스템 콜을 활용함
- `[[llm.c]] utilizes [[FlashAttention]]` — C/CUDA 환경에서 연산 대역폭 한계를 돌파하기 위해 수동으로 통합된 FlashAttention CUDA 커널 가중치 코드를 결합함

## PKM 시사점

llm.c는 AI 에이전트 LTM의 **"초경량 런타임 가동"** 지향점이다. 무거운 가상환경과 무수한 의존성 라이브러리(Python Heavy Stack)에 의존하는 에이전트 시스템은 엣지 서버 환경에서 생존하기 어렵다. DuckDB와 마크다운 파일시스템 위에서 로컬 파일 스캔만으로 동작하는 본 프레임워크 엔진의 경량화 설계 철학은 llm.c와 정확히 궤를 같이한다.

## Sources

- [Karpathy GitHub - llm.c 공식 레포지토리](https://github.com/karpathy/llm.c)
