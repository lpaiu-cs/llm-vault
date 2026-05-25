---
id: concept_rule_based_ai
title: Rule-based AI
aliases:
  - 규칙 기반 AI
  - 전문가 시스템
  - 휴리스틱 AI
type: Concept
moc: "[[Philosophy MOC]]"
parent_moc: "[[Philosophy MOC]]"
tags:
  - AI/Philosophy
  - History
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: 3e4f5a6b-7c8d-9e0f-1a2b-3c4d5e6f7a8b
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 1
related_nodes:
  - "[[The Bitter Lesson]]"
---

# Rule-based AI

인간 전문가의 지식, 도메인 휴리스틱, 수동으로 깎아 만든 특징 공학(Feature Engineering) 규칙들을 시스템 내부에 하드코딩하여 구현한 **초기 형태의 인공지능 및 언어 처리 시스템**. 체스의 오프닝 북 사전이나 기계 번역 초기 시절의 수동 문법 파서 체계가 대표적이다.

## 핵심 메커니즘

1. 지식 주입: 인간이 사유한 도메인 정수를 기계가 이해할 수 있는 정형 논리(First-order logic 등)로 번역하여 데이터베이스화
2. 휴리스틱 탐색: 사람이 규정한 평가지표와 분기 트리를 따라 제한된 연산 가중치 범위 내에서 최적 대안을 연산

## 핵심 엣지

- `[[The Bitter Lesson]] contradicts [[Rule-based AI]]` — 인간의 주관적 지식이나 수동 기법을 신경망 시스템에 주입하려는 모든 시도는 하드웨어 컴퓨테이션 스케일링을 활용한 범용 신경망에 장기적으로 패배한다는 선언

## Sources

- [The Bitter Lesson — Rich Sutton](http://www.incompleteideas.net/IncIdeas/BitterLesson.html)
