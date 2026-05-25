---
id: concept_llm_os
title: LLM OS
aliases:
  - LLM 운영체제
  - Large Language Model Operating System
type: Concept
moc: "[[Architecture MOC]]"
parent_moc: "[[Architecture MOC]]"
tags:
  - AI/Architecture
  - OperatingSystem
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: b3c4d5e6-f7a8-4b9c-cdde-2345678901cd
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 3
related_nodes:
  - "[[Context Window]]"
  - "[[Tool Use]]"
  - "[[Software 3.0]]"
---

# LLM OS

LLM을 단순한 텍스트 변환기나 챗봇이 아닌, **새로운 패러다임의 CPU 및 하드웨어 리소스 제어 커널**로 바라보는 아키텍처 메타포. 추론 엔진이 CPU 런타임이 되고, 내부의 제한된 콘텍스트 장벽이 RAM 역할을 수행하며, 외부 API 및 로컬 파일시스템 툴이 주변장치(Peripherals)로 매핑된다.

## 핵심 메커니즘

1. **추론 커널(CPU)**: 다음 토큰 예측 프로세스(Forward Pass)를 지속적으로 순환하며 연산을 지속하는 코어 프로세스
2. **휘발성 메모리(RAM)**: `[[Context Window]]` 내에 현재 가동 중인 프롬프트, 에이전트의 상태, RAG 맥락을 적재
3. **주변기기 I/O**: `[[Tool Use]]` 인터페이스를 통해 코드 인터프리터, 웹 브라우저 등 하드웨어 리소스를 에이전트 루프 안으로 바인딩

## 핵심 엣지

- `[[LLM OS]] requires [[Context Window]]` — 운영체제의 RAM에 해당하는 물리적 공간이 전제 조건으로 요구됨
- `[[LLM OS]] abstracts [[Tool Use]]` — 복잡한 툴 호출 및 라우팅 프로토콜을 한 층 위에서 운영체제 형태로 추상화함 (헌법 §1에 따라 `abstracts`가 `utilizes`를 함의하므로 별도 utilizes 엣지는 제거됨 — v1.0.2 리팩토링)

## PKM 시사점

본 Vault 역시 이 아키텍처의 **파일시스템(하드디스크)** 역할을 수행한다. 에이전트는 사용자의 질문을 받으면 LLM OS 커널을 작동시켜 본 보관소에서 관련 원자 노드를 RAG 캐시(RAM)에 페이지 인(Page-in)하는 방식으로 사유한다.

## Sources

- [Andrej Karpathy — 신년 에세이 및 강연 발언 자료 (2024-2025)](https://x.com/karpathy)
