---
title: Agent Memory Retrieval Weighting
type: contradiction
status: open
confidence: medium
aliases: [unresolved contradictions retrieval, include review meta layers, contradiction-preserving memory]
---

# Agent Memory Retrieval Weighting

### [open] Agent Memory Retrieval Weighting

## Conflict

Claim A: Review items should be excluded by default so unresolved claims do not
pollute normal retrieval.

Claim B: Review items should remain easy to surface because unresolved
uncertainty is often exactly what an agent needs during design work.

## Current Handling

Default retrieval excludes review and meta layers, including
`70_Contradictions/` and `80_Reviews/`. Agents can explicitly opt in with
`include_reviews=true` when unresolved context is relevant to the task.

If the question is "When should unresolved contradictions be included in
retrieval?", the answer is: include them when the task is explicitly about
uncertainty, conflict resolution, design tradeoffs, or human review.

## Why It Matters

The contradiction is intentional: unresolved material should not silently become
durable knowledge, but the system must preserve it so agents and humans can
inspect it during design, debugging, or review.

## Core Edges

- `[[Agent Memory Retrieval Weighting]] utilizes [[Needs Human Review]]` — unresolved retrieval tradeoffs should remain visible in the review surface.
- `[[Agent Memory Retrieval Weighting]] utilizes [[2026-06-01-route-uncertain-memory-to-review-queue]]` — the current handling follows the demo decision for uncertain memory.
- `[[Agent Memory Retrieval Weighting]] extends [[Agent Memory]]` — the weighting conflict qualifies the normal durable-memory retrieval path.

## Sources

- `docs/MCP_TOOLS.md`
- `50_Source_Summaries/chats/Source Summary - Agent Memory Session.md`
