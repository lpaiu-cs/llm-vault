---
id: source_summary_example
title: Source Summary — example
type: SourceSummary
moc: "[[Example MOC]]"
status: active
confidence: medium
created: 2026-01-01
updated: 2026-01-01
version: 1.0
node_id: a1111111-0000-4000-8000-000000000006
source_path: 06_Raw/papers/example-tokenization-notes.md
embedding_model: null
embedding_hash: null
last_indexed: null
predicate_count: 0
related_nodes:
  - "[[Byte Pair Encoding]]"
---

# Source Summary — example

> **예시 노드(example)입니다.** source-summary 노드가 `06_Raw/`의 원본을 그래프상
> 대리(proxy)하는 방식을 보여줍니다. 이 요약은 mini-vault에 포함된 synthetic raw
> 파일을 가리킵니다.

`source_path`로 원본 위치를 가리키되, 해석/요약은 이 노드에 둔다. 원본(raw)은 그래프
node가 아니며 전문검색 전용으로만 인덱싱된다는 프레임워크 규칙을 시연한다.

## 요약

- 토큰화는 글자 단위 작업을 간접적으로 만든다([[Byte Pair Encoding]] 참고).
- 출처: `06_Raw/papers/example-tokenization-notes.md`
