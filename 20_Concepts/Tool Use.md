---
id: concept_tool_use
title: Tool Use
aliases:
  - 도구 사용
  - Function Calling
  - 에이전트 도구 인터페이스
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
node_id: 1c2d3e4f-5a6b-7c8d-9e0f-1a2b3c4d5e6f
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 2
related_nodes:
  - "[[LLM OS]]"
  - "[[Software 3.0]]"
---

# Tool Use

LLM이 자체 가중치 내에 존재하지 않는 외부 세계의 지식이나 연산 능력을 보완하기 위해, **웹 브라우저, 코드 인터프리터, 파일시스템 API 등을 선택하고 실행 인수를 생성하는 아키텍처 패턴**. 카파시의 LLM OS 멘탈 모델에서 컴퓨터의 '주변장치 IO 인터페이스'에 대응되는 개념이다.

## 핵심 메커니즘

1. 도구 묘사(Tool Description): 에이전트 시스템 프롬프트(XML/JSON) 내에 사용 가능한 도구의 기능과 입력 스키마 명세를 자연어로 인입
2. 인수 생성(Argument Generation): LLM이 컨텍스트를 분석하여 도구를 실행할 최적의 타이밍을 판단하고, 정형화된 데이터 포맷(주로 JSON 구조)으로 인수를 출력
3. 실행 및 관찰(Execution and Observation): 에이전트 런타임 호스트가 가상환경 내부에서 실제 도구를 구동한 뒤, 반환된 로우 데이터를 다시 LLM의 컨텍스트 윈도우(RAM)에 페이징 인

## 핵심 엣지

- `[[LLM OS]] abstracts [[Tool Use]]` — 운영체제 메타포가 하위 도구 호출 및 파싱 프로토콜의 복잡도를 한 층 위에서 캡슐화함
- `[[Software 3.0]] requires [[Tool Use]]` — 자연어 명령과 에이전트 시퀀스가 실제 외부 세계와 IO를 수행하기 위한 물리적 필수 전제 조건임

## Sources

- [Intro to Large Language Models — Karpathy](https://www.youtube.com/watch?v=zjkBMFhNj_g)
