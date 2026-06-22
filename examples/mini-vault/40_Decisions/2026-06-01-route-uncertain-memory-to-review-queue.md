---
title: 2026-06-01-route-uncertain-memory-to-review-queue
type: decision
status: active
confidence: high
---

# Route uncertain memory to the review queue

## Decision

When an agent encounters a useful but uncertain memory claim, it should route the
claim to `80_Reviews/` instead of promoting it directly into `20_Concepts/`.

## Context

The raw session says that persistent memory should not turn every guess into
permanent truth. The source summary captures the same rule as a reusable
workflow.

## Consequences

- Durable concept notes stay smaller and more reliable.
- Unresolved claims remain visible to humans.
- Retrieval can include review items only when unresolved context is needed.

## Core Edges

- `[[2026-06-01-route-uncertain-memory-to-review-queue]] utilizes [[Human Review Queue]]` — the decision uses the review queue as the routing mechanism for uncertain claims.

## Sources

- `50_Source_Summaries/chats/Source Summary - Agent Memory Session.md`
- `06_Raw/chats/2026-06-01-agent-memory-session.md`
