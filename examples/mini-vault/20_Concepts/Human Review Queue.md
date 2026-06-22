---
title: Human Review Queue
type: Concept
status: evergreen
confidence: high
---

# Human Review Queue

A human review queue is the place where an agent stores claims that are useful
enough to remember but not safe enough to treat as verified knowledge.

In `llm-vault`, review items live under `80_Reviews/` and can be inspected with
the `review_queue` MCP tool.

## Core Edges

- `[[Human Review Queue]] implemented_by [[Needs Human Review]]` — the demo review file shows one concrete unresolved item.

## Sources

- `06_Raw/chats/2026-06-01-agent-memory-session.md`
