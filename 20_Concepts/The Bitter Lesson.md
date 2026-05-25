---
id: concept_bitter_lesson
title: The Bitter Lesson
aliases:
  - 쓰라린 교훈
  - Sutton's Bitter Lesson
  - Computation Scaling Principle
type: Concept
moc: "[[Philosophy MOC]]"
parent_moc: "[[Philosophy MOC]]"
tags:
  - AI
  - Philosophy
  - Sutton
  - Scaling
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: e5f6a7b8-c9d0-4123-efab-5678901234ef
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 3
related_nodes:
  - "[[Software 2.0]]"
  - "[[Rule-based AI]]"
  - "[[Scaling Laws]]"
source_urls:
  - http://www.incompleteideas.net/IncIdeas/BitterLesson.html
---

# The Bitter Lesson

2019년 Rich Sutton의 짧은 에세이로, **"70년 AI 역사에서 가장 큰 교훈은 인간 지식·휴리스틱을 주입한 시스템은 단기적으로 우월해 보이나, 장기적으로 컴퓨테이션 확장(Computation Scaling)을 이용한 범용 학습 알고리즘에 반드시 패배한다"**는 관찰. Karpathy가 LLM 설계·교육 철학 전반에서 가장 자주 인용하는 외부 텍스트.

## 핵심 사례

1. **체스 (1997)**: 인간 전략 주입 vs 알파-베타 탐색 + 컴퓨테이션 → 후자 승리
2. **바둑 (2016)**: 인간 패턴 주입 vs 셀프 플레이 + RL + 컴퓨테이션 → 후자 승리
3. **음성·비전·NLP**: 손으로 만든 특징(feature engineering) vs 종단간 학습 → 후자 승리
4. **LLM (2020+)**: 정교한 프롬프트 엔지니어링 vs 더 큰 모델 + 더 많은 데이터 → 후자가 일관되게 승리

## 핵심 엣지

- `[[The Bitter Lesson]] contradicts [[Rule-based AI]]` — 인간 휴리스틱 우월성 주장의 정면 부정
- `[[The Bitter Lesson]] implemented_by [[Software 2.0]]` — 추상 원리(컴퓨테이션 우위)가 Software 2.0이라는 구체 패러다임으로 실현됨 (§2.3 defines vs implemented_by 적용)
- `[[The Bitter Lesson]] implemented_by [[Scaling Laws]]` — 동일 원리가 정량 법칙으로도 구체화됨

## PKM 시사점

지식 그래프 설계에도 동일한 교훈이 적용된다. 인간이 정교하게 큐레이션한 폴더 트리는 단기적으로 깔끔하지만, **노트 수가 폭증하면 자연 발생하는 그래프 군집(Software 2.0적 접근)에 일관성·확장성에서 진다**. 4대 MOC + 9개 술어로 최소 골격만 강제하고 나머지는 데이터에 맡기는 본 프레임워크의 설계 근거.

## Sources

- [The Bitter Lesson — Rich Sutton (2019)](http://www.incompleteideas.net/IncIdeas/BitterLesson.html)
