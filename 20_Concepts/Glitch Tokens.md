---
id: concept_glitch_tokens
title: Glitch Tokens
aliases:
  - 글리치 토큰
  - 불량 토큰
  - SolidGoldMagikarp
type: Concept
moc: "[[Architecture MOC]]"
parent_moc: "[[Architecture MOC]]"
tags:
  - AI/Architecture
  - Failure-Mode
  - Tokenization
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: 0b1c2d3e-4f5a-6b7c-8d9e-0f1a2b3c4d5e
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 2
related_nodes:
  - "[[Byte Pair Encoding]]"
  - "[[Tokenizer]]"
  - "[[System 1 추론]]"
---

# Glitch Tokens

토크나이저 어휘 사전(Vocabulary)에는 등록되어 존재하나, 사전 학습(Pre-training) 코퍼스 정제 과정에서의 스크래핑 오류 등으로 인해 **가중치 학습이 전혀 이루어지지 않은 유령 토큰 영역**. 모델 인퍼런스 시 해당 토큰이 인입되면 임베딩 벡터 공간의 원점에서 길을 잃고 엉뚱한 로짓으로 튀어, 기괴한 단어 출력이나 시스템 추론 붕괴를 유발한다. (예: `SolidGoldMagikarp`, `StreamPlot`)

## 핵심 메커니즘

1. **학습 데이터 비대칭**: Reddit 스크래핑 데이터나 소스 코드 내의 고유 변수명이 토크나이저 사전에 등록되었으나, 실제 가중치 백프로파게이션 훈련 시에는 해당 문자열이 배제됨
2. **임베딩 공간 격리**: 훈련 단계에서 그라디언트 업데이트를 받지 못해 초기 무작위(Random Initialization) 상태의 가중치 벡터 공간에 고정 배치됨
3. **가중치 폭주**: 에이전트가 해당 토큰을 입력받으면 레이어를 거치며 이상 가중치가 증폭되어 예측 불가능한 환각 출력을 유도

## 핵심 엣지

- `[[Byte Pair Encoding]] causes [[Glitch Tokens]]` — 오직 기계적 빈도에만 집착하는 BPE의 통계적 속성이 불량 가중치 격리 현상을 필연적으로 유발함
- `[[Glitch Tokens]] requires [[Tokenizer]]` — 문자-토큰 매핑 사전의 불완전한 관리 상태 위에서만 유령 토큰이 정의 조건으로 성립할 수 있음

## PKM 시사점

지식 그래프에도 인덱서 파서 버그나 휴먼 에러로 인해 링크는 연결되어 있으나 실제 실체 마크다운 파일이 존재하지 않는 **'Dangling Entity(고스트 노드)'** 가 다수 발생한다. LTM 백엔드가 이를 방치하면 가중치 전파 서치 시 에러가 누적되므로, 인덱서 가동 보고서를 통해 주기적으로 글리치 엔티티를 정제·제거해 주어야 한다.

## Sources

- [Andrej Karpathy YouTube — Let's build the GPT Tokenizer](https://www.youtube.com/watch?v=zduSFxRajkE)
