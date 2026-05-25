---
id: concept_gradient_descent
title: Gradient Descent
aliases:
  - 경사 하강법
  - 역전파 최적화
type: Concept
moc: "[[Implementation MOC]]"
parent_moc: "[[Implementation MOC]]"
tags:
  - AI/Implementation
  - Math
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: 4f5a6b7c-8d9e-0f1a-2b3c-4d5e6f7a8b9c
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 1
related_nodes:
  - "[[Software 2.0]]"
---

# Gradient Descent

모델이 출력한 예측치와 데이터셋 정답(Label) 사이의 손실 함수(Loss Function) 편미분을 통해 가중치 파라미터(theta)에 대한 기울기(Gradient)를 구하고, **해당 경사도를 따라 가중치 공간을 역방향으로 업데이트하여 손실 값을 최소화하는 수학적 최적화 알고리즘**. Software 2.0 프로그램을 자동으로 찾아내는 컴파일러의 실질적 동력원이다.

## 핵심 메커니즘

1. 순방향 전파(Forward Pass): 입력 데이터를 가중치 매트릭스에 통과시켜 최종 로짓 벡터 및 손실 비용 도출
2. 오차 역전파(Backpropagation): 미분의 연쇄 법칙(Chain Rule)을 이용하여 출력층부터 입력층까지 거꾸로 올라가며 각 매개변수 레이어의 그래디언트 산출
3. 가중치 업데이트: 지정된 학습률(Learning Rate)을 곱해 가중치 평면의 전역 최적점(Global Minimum)을 향해 파라미터를 점진적으로 이동

## 핵심 엣지

- `[[Software 2.0]] requires [[Gradient Descent]]` — 데이터 명세에서 프로그램을 자동으로 탐색해내는 경사 하강 최적화 수학 기법이 없으면 2.0 패러다임은 구동될 수 없음

## Sources

- [Software 2.0 — Karpathy Medium Essay](https://karpathy.medium.com/software-2-0-a64152b37c35)
