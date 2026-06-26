# Why ltm-vault?

LLM agents need long-term memory, but naive memory systems turn mistakes into
permanent state. A note that was guessed, outdated, contradicted, or never
reviewed can later be retrieved as if it were verified truth.

`ltm-vault` is built around a stricter premise: agent memory must preserve
evidence, uncertainty, and review state.

## The Problem

Plain chat history and simple vector search are useful, but they do not answer
the operational questions that matter in long-running work:

- Where did this claim come from?
- Is the source immutable, summarized, inferred, or unreviewed?
- Which decision replaced an older one?
- Which assumptions are known to be stale?
- Which contradictions should remain visible instead of being smoothed over?
- Can an agent write memory without polluting the durable knowledge graph?

If those questions are not represented in the system, the agent can retrieve a
confident-looking memory while losing the audit trail that made it safe to use.

## Design Principles

**Raw sources are evidence, not editable notes.**
`06_Raw/` is treated as immutable after ingest. If interpretation changes, update
a source summary, concept, project dashboard, or decision record instead of
rewriting the evidence.

**Summaries cite sources.**
Durable knowledge should be connected back to raw source paths or external URLs.
The system distinguishes source material from an agent's own inference.

**Decisions are append-only by default.**
Important choices live in `40_Decisions/`. When a decision changes, create a new
record and mark the old one as superseded instead of silently editing history.

**Contradictions are preserved.**
Conflicting claims go to `70_Contradictions/`. The default behavior is to keep
both sides visible until a human or later source resolves the conflict.

**Uncertainty has a route.**
Low-confidence claims, possible hallucinations, and items needing human judgment
go to `80_Reviews/`. The review queue is part of the runtime, not an afterthought.

**Retrieval is layer-aware.**
The retriever ranks interpreted knowledge higher than raw or low-confidence
material, excludes review/meta layers by default, and can include them when the
agent explicitly needs unresolved context.

**The framework and the private vault are separate.**
The framework contains policies, engine code, docs, scripts, and examples. A real
personal or team memory instance should keep private knowledge in a separate
clone or branch and avoid pushing raw sources, project notes, or personal
decisions into the framework skeleton.

## Why Not Just RAG?

RAG usually answers "what text is similar to this question?" `ltm-vault` also
asks "what kind of text is this, how trustworthy is it, and how should an agent
act on it?"

That difference matters when memory is written by agents. The goal is not only
recall. The goal is auditable recall with enough structure for agents to avoid
treating every retrieved sentence as verified truth.

## What MCP Adds

The MCP server exposes both read and write workflows:

- `retrieve_knowledge` for hybrid BM25/dense/graph retrieval
- `review_queue` for unresolved questions, contradictions, and review items
- `create_node`, `update_node`, and edge tools for controlled memory writes
- `sync_vault` and `reconcile_graph` for keeping Markdown and DuckDB aligned

This lets an agent use the vault as a working memory substrate while still
respecting the vault's source, review, and ontology rules.

## Minimal Success Criteria

A good `ltm-vault` instance should make these behaviors easy to verify:

- a raw source can be ingested without becoming a graph node;
- a source summary can cite that raw source;
- a decision can point to the source summary or policy that justified it;
- a contradiction can be logged without overwriting either side;
- a review queue can show unresolved low-confidence claims;
- retrieval can surface useful context while labeling layer, status, and
  confidence.
