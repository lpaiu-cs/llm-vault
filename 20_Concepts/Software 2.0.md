---
id: concept_software_2_0
title: Software 2.0
aliases:
  - 소프트웨어 2.0
  - Neural Network Programming
  - Differentiable Programming
type: Concept
moc: "[[Philosophy MOC]]"
parent_moc: "[[Philosophy MOC]]"
tags:
  - AI/LLM
  - Paradigm
  - Karpathy
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: b2c3d4e5-f6a7-4890-bcde-2345678901bc
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 4
related_nodes:
  - "[[Software 3.0]]"
  - "[[The Bitter Lesson]]"
  - "[[Gradient Descent]]"
  - "[[Software 1.0]]"
source_urls:
  - https://karpathy.medium.com/software-2-0-a64152b37c35
---

# Software 2.0

코드를 인간이 직접 작성(Rule-based)하는 대신, **데이터셋과 손실 함수(Loss Function)를 정의하고 신경망을 훈련(Gradient Descent)하여 프로그램을 자동으로 탐색**하는 패러다임. Karpathy가 2017년 Medium 에세이에서 명명했다. Software 1.0이 명령어 시퀀스의 집합이라면, Software 2.0은 가중치 공간(Weight Space) 안에서의 탐색 결과물이다.

## 핵심 메커니즘

1. **명세(Spec) 정의**: 원하는 입출력 동작을 데이터셋 형태로 표현
2. **손실 함수 설계**: 모델 출력과 정답 사이 거리를 정량화
3. **경사 하강(Gradient Descent)**: 손실을 최소화하는 가중치 조합을 자동 탐색
4. **컴파일 산출물**: 사람이 읽을 수 없는 가중치 행렬이지만 명세는 만족

## 핵심 엣지

- `[[Software 2.0]] contradicts [[Software 1.0]]` — 명령형 코드 vs 데이터 기반 프로그램 탐색
- `[[Software 3.0]] extends [[Software 2.0]]` — 가중치 훈련에서 자연어 프롬프트로 추상화 레이어 상승
- `[[Software 2.0]] requires [[Gradient Descent]]` — 최적화 알고리즘 없이는 프로그램 탐색 불가
- `[[The Bitter Lesson]] implemented_by [[Software 2.0]]` — Sutton의 추상 원리(컴퓨테이션 우위)가 Software 2.0이라는 구체 패러다임으로 실현됨 (§2.3 적용)

## PKM 시사점

지식 베이스 설계 측면에서, **고정된 규칙 기반 분류 체계(폴더 트리)는 Software 1.0적 사고**이며, **데이터(노트)와 관계(엣지)에서 자연 발생하는 그래프 군집**이 Software 2.0적 사고에 가깝다. Obsidian의 그래프 뷰가 본질적으로 이 패러다임에 부합하는 이유.

## Sources

- [Software 2.0 — Andrej Karpathy (2017)](https://karpathy.medium.com/software-2-0-a64152b37c35)
