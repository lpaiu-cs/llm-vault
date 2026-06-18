---
id: concept_example_tokenizer
title: Tokenizer
aliases:
  - 토크나이저
type: Concept
moc: "[[Example MOC]]"
parent_moc: "[[Example MOC]]"
tags:
  - Example
  - Tokenization
status: evergreen
created: 2026-01-01
updated: 2026-01-01
version: 1.0
node_id: a1111111-0000-4000-8000-000000000001
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 1
related_nodes:
  - "[[Byte Pair Encoding]]"
---

# Tokenizer

> **예시 노드(example)입니다.** 이 mini-vault는 프레임워크의 구조·검색·그래프 동작을
> 보여주기 위한 최소 데모 코퍼스입니다. 실제 지식이 아닙니다.

원시 문자열을 모델이 다루는 **정수 토큰 ID 시퀀스**로 바꾸는 전처리 시스템. 모델은
개별 문자가 아니라 토큰 단위로 입력을 본다.

## 글자가 아니라 토큰을 본다

`strawberry`처럼 한 단어가 여러 토큰 조각으로 묶이면(자세히는 [[Byte Pair Encoding]]),
글자 `r`은 토큰 안에 흡수돼 직접 보이지 않는다. 그래서 "단어 안의 글자 수 세기"는
본질적으로 간접적이 된다 — 불가능한 것은 아니지만 단순해 보이는 글자 과제가 왜
취약할 수 있는지를 설명해 준다.

## 핵심 엣지

- `[[Tokenizer]] implemented_by [[Byte Pair Encoding]]` — 토큰화 추상 명세가 빈도 기반
  서브워드 알고리즘으로 실체화됨
