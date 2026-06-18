---
id: concept_example_bpe
title: Byte Pair Encoding
aliases:
  - BPE
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
node_id: a1111111-0000-4000-8000-000000000002
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 0
related_nodes:
  - "[[Tokenizer]]"
---

# Byte Pair Encoding

> **예시 노드(example)입니다.** mini-vault 데모 코퍼스의 일부입니다.

가장 빈번한 문자/바이트 쌍을 반복적으로 하나의 토큰으로 병합해 나가는 통계적 서브워드
토큰화 알고리즘. 언어학 지식 없이 빈도수만으로 어휘 사전을 빌드한다.

## 사례: 글자 단위가 가려지는 이유

`strawberry`는 BPE 병합 결과 하나의 글자 시퀀스가 아니라 여러 서브워드 토큰 조각으로
나뉜다(예: `st` + `raw` + `berry` 식 — 정확한 분할은 토크나이저·버전에 따라 다르다).
모델이 보는 단위는 이 토큰 ID 배열이지 개별 글자 `r`이 아니다. 그래서 글자 세기 과제는
토큰 경계 뒤에 글자 정보가 가려져 직접적이지 않다(불가능한 것은 아님).
