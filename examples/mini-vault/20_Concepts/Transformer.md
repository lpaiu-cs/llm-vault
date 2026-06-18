---
id: concept_example_transformer
title: Transformer
aliases:
  - 트랜스포머
type: Concept
moc: "[[Example MOC]]"
parent_moc: "[[Example MOC]]"
tags:
  - Example
  - Architecture
status: evergreen
created: 2026-01-01
updated: 2026-01-01
version: 1.0
node_id: a1111111-0000-4000-8000-000000000003
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 1
related_nodes:
  - "[[Tokenizer]]"
---

# Transformer

> **예시 노드(example)입니다.** mini-vault 데모 코퍼스의 일부입니다.

self-attention을 핵심 연산으로 삼아 시퀀스 내 토큰 간 관계를 병렬로 학습하는 신경망
아키텍처. 입력은 [[Tokenizer]]가 만든 토큰 ID 시퀀스다.

## 핵심 엣지

- `[[Transformer]] requires [[Tokenizer]]` — 트랜스포머는 토큰화된 정수 시퀀스를 입력
  전제로 한다
