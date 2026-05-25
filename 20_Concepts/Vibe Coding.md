---
id: concept_vibe_coding
title: Vibe Coding
aliases:
  - 바이브 코딩
  - Intent-Driven Coding
  - Flow Coding
type: Concept
moc: "[[Philosophy MOC]]"
parent_moc: "[[Philosophy MOC]]"
tags:
  - AI/LLM
  - DeveloperExperience
  - 2025
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: d4e5f6a7-b8c9-4012-defa-4567890123de
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 3
related_nodes:
  - "[[Software 3.0]]"
  - "[[LLM OS]]"
  - "[[Hallucination as Default]]"
source_urls:
  - https://x.com/karpathy/status/1886192184808149383
---

# Vibe Coding

2025년 2월 Karpathy가 X에서 명명한 개발 스타일. **개발자는 자연어로 고차원 의도(Intent)와 흐름(Vibe)을 제시하고, AI 에이전트가 로우 레벨 문법·디버깅·실행을 전담**한다. 코드를 직접 쓰지 않고 프로젝트의 분위기를 지휘하는 형태. Karpathy 원문 요지: *"It's not really coding — I just see things, say things, run things, and copy-paste things, and it mostly works."*

## 핵심 메커니즘

1. **의도 표현**: 자연어로 원하는 동작이나 느낌을 서술 ("이거 좀 더 부드럽게", "에러 무시하고 일단 돌려봐")
2. **AI 구현**: Cursor·Claude·Codex 등이 실제 코드 생성·실행
3. **결과 관찰 후 흐름 조정**: 코드를 읽지 않고 동작만 확인하며 다음 의도 지시
4. **누적 산출물**: 프로토타입·스크립트 수준에서 강력, 프로덕션 코드는 별도 검증 필요

## 핵심 엣지

- `[[Vibe Coding]] requires [[Software 3.0]]` — LLM이 런타임을 점유한 환경이 전제
- `[[Vibe Coding]] utilizes [[LLM OS]]` — 코드 인터프리터·파일시스템·터미널을 도구로 사용
- `[[Vibe Coding]] requires [[Reflection Loop]]` — 코드를 직접 읽지 않으므로, 책임 있는 Vibe Coding은 환각 검증 루프를 전제 조건으로 요구 (§2.4 causes vs requires 적용)

## PKM 시사점

본 Vault의 원자 노트 작성도 Vibe Coding 스타일로 가능하다. *"Karpathy의 Software 2.0 노트 만들어줘 — Philosophy MOC 하위로, 9개 술어 중 contradicts 하나는 꼭 써줘"* 같은 의도만 명시하면 에이전트가 4대원칙·Frontmatter·엣지를 자동 채움. 본 노트 자체가 그 사례.

## Sources

- [Karpathy 원문 트윗 (2025-02-02)](https://x.com/karpathy/status/1886192184808149383)
