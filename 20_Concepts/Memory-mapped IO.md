---
id: concept_memory_mapped_io
title: Memory-mapped IO
aliases:
  - mmap
  - 메모리 맵 IO
type: Concept
moc: "[[Implementation MOC]]"
parent_moc: "[[Implementation MOC]]"
tags:
  - AI/Implementation
  - OperatingSystem
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: f8a9b0c1-d2e3-4456-abcd-789012345fbc
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 2
related_nodes:
  - "[[llm.c]]"
  - "[[Context Window]]"
---

# Memory-mapped IO

운영체제(OS) 커널의 시스템 콜 `mmap`을 활용하여 **로컬 디스크에 존재하는 대용량 이진 데이터 파일을 프로세스의 가상 메모리 주소 공간에 직접 매핑하는 입출력 아키텍처**. 유저 공간으로 데이터를 복사하는 중간 오버헤드가 없으며, OS 내장 페이지 캐시(Page Cache) 메커니즘을 그대로 활용하므로 기가바이트에서 테라바이트급 LLM 토큰 학습 데이터셋을 지연 없이 메모리 런타임 위로 적재할 수 있다.

## 핵심 메커니즘

1. **제로 카피(Zero-copy)**: 디스크 컨트롤러가 디바이스 데이터를 커널 공간에서 유저 버퍼로 이중 복사하는 단계 없이 가상 메모리 테이블 주소를 다이렉트로 바인딩
2. **지연 로딩(Lazy Loading)**: 파일 전체를 물리 RAM에 먼저 올리지 않고 포인터 주소만 열어둔 뒤, 프로세스가 실제로 가중치 데이터를 읽는 순간 페이지 폴트(Page Fault)를 발생시켜 필요한 청크만 디스크에서 즉시 로딩
3. **OS 자동 메모리 관리**: RAM 자원이 부족해지면 운영체제 커널이 오랫동안 참조되지 않은 지연 데이터 페이지를 자동으로 언로드(Drop)하므로 프로세스 안정성 보장

## 핵심 엣지

- `[[llm.c]] utilizes [[Memory-mapped IO]]` — 원시 데이터 가동 효율을 극대화하고 거대 토큰 파일을 동적으로 순회하기 위해 mmap 커널 시스템 콜 인터페이스를 도구로 활용함
- `[[Context Window]] requires [[Memory-mapped IO]]` — (수정 반영) 물리적 가상 메모리 주소 맵 구조 위에 디스크의 로우 코퍼스가 기계적으로 정렬되어 로딩되어야만, 트랜스포머의 인퍼런스 맥락 윈도우가 RAM 레이어 위에서 실체화될 수 있음

## PKM 시사점

Memory-mapped IO는 **"지연 로딩(Lazy Loading)을 통한 자원 제어"** 의 정수이다. 본 Obsidian 프레임워크가 추구하는 미래 LTM 아키텍처 역시 사용자의 산발적 질문에 맞춰 DuckDB 테이블의 인덱스 가중치 포인터만 열어두고, 검증 루프가 가동되는 순간에만 해당 마크다운 노드의 본문을 부분 적재(Page Fault 처리)하는 메커니즘으로 동작해야 메모리 폭증을 막을 수 있다.

## Sources

- [Andrej Karpathy GitHub - llm.c 데이터 로더 소스 코드 소견](https://github.com/karpathy/llm.c)
