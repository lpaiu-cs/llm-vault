---
id: concept_transformer
title: Transformer
aliases:
  - 트랜스포머
  - Attention Is All You Need
type: Concept
moc: "[[Architecture MOC]]"
parent_moc: "[[Architecture MOC]]"
tags:
  - AI/Architecture
  - NeuralNetwork
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: c4d5e6f7-a8b9-4c0d-deef-3456789012de
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 2
related_nodes:
  - "[[nanoGPT]]"
  - "[[Software 2.0]]"
  - "[[The Bitter Lesson]]"
---

# Transformer

2017년 Vaswani 등이 제안한 **Self-Attention 메커니즘 기반의 신경망 아키텍처**. 합성곱(CNN)이나 순환(RNN) 구조를 완전히 배제하고, 입력 데이터 내부의 모든 토큰 간 관계 가중치를 동시 연산(Parallelism)하여 대규모 스케일링의 문을 열었다. 현재 존재하는 모든 거대 언어 모델(LLM)의 물리적 근간이다.

## 핵심 메커니즘

1. **Self-Attention**: 문장 내의 모든 단어가 서로에게 미치는 영향도를 쿼리(Query), 키(Key), 밸류(Value) 행렬 연산을 통해 동적 산출
2. **Positional Encoding**: 순차적 가동을 하지 않는 병렬 구조의 한계를 극복하기 위해 토큰의 위치 정보를 가중치 벡터에 직접 주입
3. **Residual Connection**: 레이어가 깊어져도 그래디언트 소실 없이 학습이 가능하게 만드는 우회 통로 설계

## 핵심 엣지

- `[[Transformer]] implemented_by [[nanoGPT]]` — 추상적 아키텍처 명세가 카파시의 최소 가독 가중치 코드로 구현됨
- `[[The Bitter Lesson]] implemented_by [[Transformer]]` — 컴퓨테이션 스케일링 법칙을 온전히 누릴 수 있는 구조를 제공함으로써 Sutton의 교훈을 물리적으로 증명함

## PKM 시사점

Transformer의 Attention 행렬은 **밀집 그래프(Dense Graph)** 와 같다. 모든 단어가 서로 연결된 구조 속에서 의미를 추출하듯, 본 Obsidian 보관소 또한 노드 간의 느슨한 연결 관계 속에서 의미적 가중치 클러스터(Graphify 뷰)를 자연 발생시킨다.

## Sources

- [Vaswani et al. (2017) — Attention Is All You Need](https://arxiv.org/abs/1706.03762)
