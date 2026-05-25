---
id: concept_hallucination_default
title: Hallucination as Default
aliases:
  - 디폴트 환각
  - Dreaming Machine
  - LLM Hallucination
type: Concept
moc: "[[Philosophy MOC]]"
parent_moc: "[[Philosophy MOC]]"
tags:
  - AI/LLM
  - Failure-Mode
  - Karpathy
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: f6a7b8c9-d0e1-4234-fabc-6789012345fa
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 3
related_nodes:
  - "[[Reflection Loop]]"
  - "[[System 1 추론]]"
  - "[[Base Model]]"
  - "[[RAG]]"
source_urls:
  - https://www.youtube.com/watch?v=zjkBMFhNj_g
---

# Hallucination as Default

Karpathy의 핵심 관점: **"LLM은 본질적으로 끊임없이 환각을 생성하는 Dreaming Machine이며, 사실 발화는 프롬프트·데이터·RLHF에 의해 정교하게 통제된 운 좋은 환각일 뿐"**. 환각은 버그가 아니라 LLM의 디폴트 작동 양식이며, 정확성은 그 위에 덧붙인 가드레일의 결과물이다.

## 핵심 메커니즘

1. **Base Model의 본성**: 사전학습된 모델은 "그럴듯한 다음 토큰"을 확률적으로 샘플링할 뿐 사실 여부 검증 메커니즘 없음
2. **System 1의 한계**: 단일 Forward Pass는 자기검증 단계가 없어 환각이 즉시 출력으로 흘러나감
3. **RLHF의 역할**: 인간 피드백으로 환각의 표면적 빈도를 낮출 뿐, 본질적 메커니즘은 그대로
4. **사실성 ≠ 추론능력**: 환각이 줄어도 추론능력이 따라 오르지는 않음

## 핵심 엣지

- `[[Reflection Loop]] requires [[Hallucination as Default]]` — Reflection Loop라는 설계 패턴은 "환각이 디폴트"라는 관찰을 전제로만 존재 의미를 가짐 (방향성 함정 §2.4 적용)
- `[[System 1 추론]] causes [[Hallucination as Default]]` — 자기검증 없는 직관적 추론이 근본 원인
- `[[RAG]] utilizes [[Hallucination as Default]]` — 외부 지식 주입으로 환각을 사실로 "고정"하는 전략

## PKM 시사점

본 Vault의 LTM 시스템에서 `[[Karpathy LLM Framework MOC]]` 5.3절 Reflection Loop가 필요한 근본 이유. 에이전트가 답변에서 언급한 엔티티를 그래프에 역조회하여 존재·관계 일관성을 검증하는 것은, **환각이 디폴트라는 전제 위에서만 의미를 가지는 방어 메커니즘**. 환각을 "버그"가 아닌 "디폴트"로 받아들이면 설계가 명확해진다.

## Sources

- [Intro to Large Language Models — Karpathy](https://www.youtube.com/watch?v=zjkBMFhNj_g)
