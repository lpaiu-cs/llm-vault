---
id: concept_tokenizer
title: Tokenizer
aliases:
  - 토크나이저
  - 토큰화 프레임워크
type: Concept
moc: "[[Architecture MOC]]"
parent_moc: "[[Architecture MOC]]"
tags:
  - AI/Architecture
  - Tokenization
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: e6f7a8b9-c0d1-4e2f-fa0f-5678901234fa
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 2
related_nodes:
  - "[[Byte Pair Encoding]]"
  - "[[Glitch Tokens]]"
---

# Tokenizer

인간이 사용하는 원시 문자열 데이터(Raw Text)를 고정된 정수형 인덱스 배열(Token ID)로 변환하여 **신경망 모델 가중치 행렬에 인입시키는 서브프레임워크 및 전처리 시스템**. Karpathy가 "LLM 아키텍처에서 가장 지저분하고, 수많은 설명 불가능한 결함이 시작되는 블랙박스"라고 강하게 비판하는 영역이다.

## 핵심 메커니즘

1. **인코딩(Encoding)**: 입력 마크다운 문자를 모델 어휘 사전(Vocabulary)에 등록된 ID 배열로 매핑
2. **디코딩(Decoding)**: 모델 결과물인 로짓(Logits) 벡터에서 샘플링된 고유 ID를 다시 인간용 언어로 역변환
3. **어휘 사전 구성**: 말뭉치 스캔을 통해 최소 단위 문자부터 점진적으로 최적의 단어 파편 사전을 빌드

## 핵심 엣지

- `[[Tokenizer]] implemented_by [[Byte Pair Encoding]]` — 문자열 분할 추상 명세가 통계 빈도 기반 알고리즘인 BPE 구조를 통해 실체화됨
- `[[Glitch Tokens]] requires [[Tokenizer]]` — 토크나이저 어휘 사전 빌드 단계의 한계와 논리적 버그가 불량 토큰의 존재 전제 조건이 됨

## PKM 시사점

인간이 인지하는 지식 노드의 경계(파일명)와 에이전트가 토큰으로 쪼개서 인식하는 벡터 임베딩의 경계는 일치하지 않는다. 영문 식별자 중심의 정형화된 파일명 노드 명명을 가이드라인으로 세운 근본적인 원인이 이 토크나이저의 전처리 간섭 때문이다.

## Sources

- [Andrej Karpathy YouTube — Let's build the GPT Tokenizer](https://www.youtube.com/watch?v=zduSFxRajkE)
