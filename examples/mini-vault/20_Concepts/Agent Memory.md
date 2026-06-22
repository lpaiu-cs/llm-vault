---
title: Agent Memory
type: Concept
status: evergreen
confidence: medium
aliases: [agent-maintained memory]
---

# Agent Memory

Agent memory is persistent project context that an AI agent can retrieve and
update across sessions. In this vault, durable agent memory should remain
source-grounded and should preserve uncertainty instead of flattening it into a
confident note.

## Core Rules

- Store evidence separately from interpretation.
- Promote only durable claims into concept notes.
- Route uncertain or unreviewed claims to a review queue.
- Keep decision history append-only when a decision changes.

## Core Edges

- `[[Agent Memory]] requires [[Human Review Queue]]` — uncertain claims need a review route before they become durable memory.

## Sources

- `06_Raw/chats/2026-06-01-agent-memory-session.md`
