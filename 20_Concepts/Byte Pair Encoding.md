---
id: concept_byte_pair_encoding
title: Byte Pair Encoding
aliases:
  - BPE
  - 바이트 쌍 인코딩
type: Concept
moc: "[[Architecture MOC]]"
parent_moc: "[[Architecture MOC]]"
tags:
  - AI/Architecture
  - Tokenization
  - Algorithm
status: evergreen
created: 2026-05-25
updated: 2026-05-25
version: 1.0
node_id: f7a8b9c0-d1e2-4f3a-bb0f-6789012345fb
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 3
related_nodes:
  - "[[Tokenizer]]"
  - "[[Glitch Tokens]]"
  - "[[Context Window]]"
---

# Byte Pair Encoding

데이터 내에서 가장 빈번하게 연속되어 등장하는 문자 또는 **바이트 쌍을 반복적으로 하나의 고유 토큰으로 병합(Merge)해 나가는 통계적 서브워드 토큰화 알고리즘**. 언어학적 지식이나 어근 분석 없이 오직 빈도수 스케일링에만 의존하여 사전을 빌드한다. GPT 생태계의 표준 토크나이저 엔진이다.

## 핵심 메커니즘

1. **원시 바이트 초기화**: 모든 문자열을 바이트 단위(Byte-level)로 분해하여 시작
2. **빈도수 카운팅**: 전체 학습 코퍼스를 순회하며 인접한 두 바이트 가중치 조합의 빈도를 계산
3. **반복 병합 및 고정**: 어휘 사전 크기(Vocabulary Size) 임계치에 도달할 때까지 Top-1 빈도 쌍을 단일 토큰으로 결합

## 핵심 엣지

- `[[Tokenizer]] implemented_by [[Byte Pair Encoding]]` — 토큰화라는 추상 메커니즘이 BPE의 빈도 병합 연산을 통해 실현됨
- `[[Byte Pair Encoding]] causes [[Glitch Tokens]]` — 코퍼스 내 노이즈 데이터나 빈도 왜곡으로 인해 정상 작동을 방해하는 불량 토큰 현상을 유발함
- `[[Byte Pair Encoding]] replaces [[Character-level Model]]` — 글자 단위로 쪼개 연산 비용이 극단적으로 낭비되던 기존 로우 레벨 임베딩 스택을 기능적으로 완전히 대체함

## PKM 시사점

BPE는 언어의 문맥을 보지 않고 빈도로만 압축한다. 인간이 지식을 요약할 때도 단순 키워드 출현 빈도로만 요약하면 맥락이 소실된다. Obsidian 내 원자 노드를 생성할 때 단순 단어 덤프가 아닌, '9대 엣지 술어'라는 관계적 가이드라인을 강제 부착해야 하는 수학적 당위성이 여기에 있다.

## Sources

- [Andrej Karpathy YouTube — Let's build the GPT Tokenizer](https://www.youtube.com/watch?v=zduSFxRajkE)
