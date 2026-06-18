---
type: decision
date: 2026-01-01
status: active
project: Example Project
confidence: medium
sources:
  - examples/mini-vault/20_Concepts/Tokenizer.md
related:
  - "[[Example Project]]"
node_id: a1111111-0000-4000-8000-000000000005
---

# Example decision — 토큰 기반 카운팅 대신 외부 도구 사용

> **예시 노드(example)입니다.** 결정 기록(decision record) 형식을 보여주는 데모입니다.

## Decision

[[Example Project]]에서 글자 수 세기는 모델의 토큰 내부 추론에 맡기지 않고 외부
파이썬 도구로 처리한다.

## Context

[[Tokenizer]]/[[Byte Pair Encoding]] 때문에 글자 단위 카운팅이 간접적이라, 토이
실험에서 결과가 불안정했다.

## Consequences

- 글자 세기는 결정적 도구로, 의미 이해는 모델로 분리.
- 이 결정은 예시일 뿐이며 실제 정책이 아니다.
