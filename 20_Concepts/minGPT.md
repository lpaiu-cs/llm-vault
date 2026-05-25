---
id: concept_mingpt
title: minGPT
aliases:
  - 민GPT
  - Minimum GPT Implementation
type: Concept
moc: "[[Implementation MOC]]"
parent_moc: "[[Implementation MOC]]"
tags:
  - AI/Implementation
  - PyTorch
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: b4c5d6e7-f8a9-4012-bcde-3456789012de
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 2
related_nodes:
  - "[[Transformer]]"
  - "[[nanoGPT]]"
---

# minGPT

Andrej Karpathy가 공개한 **OpenAI GPT(Generative Pre-trained Transformer) 아키텍처의 최소 가독 전제 PyTorch 구현체**. 신경망의 블랙박스 추상화를 걷어내고, 복잡한 기능 없이 오직 가동 가능한 `[[Transformer]]` 코어 연산 메커니즘을 한눈에 파악할 수 있도록 교육적 목적으로 설계되었다.

## 핵심 메커니즘

1. **정밀한 1:1 매핑**: GPT-2 및 GPT-3의 수학적 아키텍처 명세를 PyTorch `nn.Module`과 레이어 단위로 정밀하게 대조 구현
2. **복잡성 소거**: 대규모 분산 훈련 코드가 유발하는 노이즈를 전면 소거하고, 오직 단일 GPU 또는 로컬 환경에서의 포워드/백워드 패스 흐름에만 집중
3. **훈련 및 인퍼런스 분리**: 토큰 데이터가 스케일링 가중치를 타고 흐르는 과정을 스크립트 수백 줄 내에 완벽히 격리 표기

## 핵심 엣지

- `[[Transformer]] implemented_by [[minGPT]]` — 어텐션 가중치 수학 법칙 명세가 파이토치 최소 가독 코드로 구현됨
- `[[nanoGPT]] extends [[minGPT]]` — minGPT의 가독성 중심 뼈대 위에 하드웨어 레벨 최적화를 추가하며 상위 확장됨

## PKM 시사점

minGPT는 지식 구조화의 **"가독성 우선 프로토타입"** 단계이다. 지식 관리 체계를 빌드할 때, 처음부터 거대한 자동화 인덱서와 조인 테이블을 설계하면 시스템의 직관성이 무너진다. 핵심 개념 노드를 인간이 읽기 편한 구조로 먼저 원자화하는 것이 minGPT적 접근이다.

## Sources

- [Karpathy GitHub - minGPT 공식 레포지토리](https://github.com/karpathy/minGPT)
