---
id: concept_reflection_loop
title: Reflection Loop
aliases:
  - 자가 수정 루프
  - Self-Correction
  - System 2 Verification
type: Concept
moc: "[[Architecture MOC]]"
parent_moc: "[[Architecture MOC]]"
tags:
  - AI/Architecture
  - Agent
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: 5a6b7c8d-9e0f-1a2b-3c4d-5e6f7a8b9c0d
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 2
related_nodes:
  - "[[Hallucination as Default]]"
  - "[[System 2 추론]]"
---

# Reflection Loop

에이전트가 1차 출력을 생성한 후 이를 곧바로 사용자에게 배포하지 않고, **시스템 내부 프롬프트 가드레일이나 정형화된 지식 베이스 검증 경로를 통해 결과물의 모순, 문법, 논리 오류를 스스로 재검토 및 수정(Self-Correction)하도록 제어하는 연산 아키텍처 루프**. 카파시가 주장하는 LLM의 System 2 추론을 구현하는 핵심 메커니즘이다.

## 핵심 메커니즘

1. 초안 생성(Drafting): 사용자 의도에 따라 직관적인 1차 출력 스트림 생성
2. 비판 스캔(Criticism): 별도의 프롬프트 지시나 외부 지식 그래프 덤프 조인을 가동하여 초안 내부의 결함, 혹은 온톨로지 제약(예: 9대 술어 위반 여부) 위반을 검출
3. 재작성 및 정제(Refinement): 검출된 비판 컨텍스트를 이전 RAM 캐시에 병합 주입하여, 수정된 고품질 최종 토큰을 출력 평면에 동기화

## 핵심 엣지

- `[[Reflection Loop]] requires [[Hallucination as Default]]` — 에이전트의 출력이 기본적으로 환각과 오류의 위험(Dreaming Machine)을 내포하고 있다는 존재론적 관찰 위에서만 자가 검증 루프의 설계적 당위성이 성립함
- `[[System 2 추론]] implemented_by [[Reflection Loop]]` — 고정 연산 비용을 넘어 스스로 사유의 분기를 검토해 나가는 고차원 추론 메커니즘이 자가 수정 루프 아키텍처를 통해 코드로 구체화됨

## Sources

- [Intro to Large Language Models — Karpathy](https://www.youtube.com/watch?v=zjkBMFhNj_g)
