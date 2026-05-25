---
id: concept_software_3_0
title: Software 3.0
aliases:
  - 소프트웨어 3.0
  - LLM-Native Programming
  - Prompt as Program
type: Concept
moc: "[[Philosophy MOC]]"
parent_moc: "[[Philosophy MOC]]"
tags:
  - AI/LLM
  - Paradigm
  - Agent
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: c3d4e5f6-a7b8-4901-cdef-3456789012cd
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 4
related_nodes:
  - "[[Software 2.0]]"
  - "[[LLM OS]]"
  - "[[Vibe Coding]]"
  - "[[Tool Use]]"
source_urls:
  - https://x.com/karpathy
---

# Software 3.0

가중치 훈련 단계(Software 2.0)를 넘어, **자연어 프롬프트·툴 라우팅·에이전트 루프의 조합**을 통해 소프트웨어를 가동하는 LLM 중심의 연산 패러다임. 프로그램의 단위가 코드 라인(1.0)도 아니고 가중치 텐서(2.0)도 아닌, **자연어 명령과 에이전트 행동 시퀀스**가 된다. Karpathy가 2024–2025년 강연·트윗에서 일관되게 사용하는 표현.

## 핵심 메커니즘

1. **프롬프트 = 함수 시그니처**: 입출력 명세가 자연어 문자열로 표현됨
2. **LLM = 런타임**: 프롬프트 해석·계획·도구 호출을 하나의 추론 엔진이 수행
3. **툴 라우팅**: 코드 인터프리터·웹 브라우저·파일시스템 등을 LLM이 직접 선택·호출
4. **에이전트 루프**: 결과 관찰 → 재계획 → 재실행의 반복

## 핵심 엣지

- `[[Software 3.0]] extends [[Software 2.0]]` — 훈련된 모델 위에 자연어 인터페이스 계층 추가
- `[[Software 3.0]] utilizes [[LLM OS]]` — 컨텍스트 윈도우와 툴을 운영체제처럼 사용
- `[[Software 3.0]] requires [[Tool Use]]` — 외부 세계와의 I/O 없이는 실행 능력 없음
- `[[Vibe Coding]] requires [[Software 3.0]]` — 자연어 흐름 코딩의 전제 조건

## PKM 시사점

본 Vault는 Software 3.0 시대의 **에이전트 LTM 소스 데이터**가 된다. 인간이 읽기 위한 텍스트만이 아니라, 에이전트 런타임이 컨텍스트로 적재할 수 있도록 구조화된(엣지·메타데이터) 노드 집합이어야 한다.

## Sources

- [Andrej Karpathy — X/Twitter](https://x.com/karpathy)
