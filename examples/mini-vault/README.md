# examples/mini-vault — demo corpus and eval fixture

This folder is a small, non-private vault that shows how `llm-vault` separates
raw evidence, source summaries, concepts, project dashboards, decision records,
contradictions, and review items.

It is example data only. Real personal or team knowledge belongs in a private
instance, not in this template repository.

## Contents

| Path | What it demonstrates |
|------|----------------------|
| `06_Raw/` | immutable raw source material |
| `10_MOC/` | a small map of content |
| `20_Concepts/` | durable concept nodes and 9-predicate edges |
| `30_Projects/` | a project dashboard that links out instead of duplicating detail |
| `40_Decisions/` | decision record format |
| `50_Source_Summaries/` | source summaries that cite raw evidence |
| `70_Contradictions/` | unresolved conflicts preserved instead of flattened |
| `80_Reviews/` | unresolved claims that should not become durable concepts yet |
| `eval_queries.json` | retrieval evaluation queries |

## Build The Fixture

From the repository root:

```bash
python3 90_Engine/indexer.py \
  --vault examples/mini-vault \
  --db fixture.db \
  --force \
  --report
```

The relative `--db fixture.db` path is resolved under the mini-vault root, so it
creates `examples/mini-vault/fixture.db`. That file is generated and ignored by
git. Add `--embed` if Ollama and the embedding model are running.

## Try Retrieval

```bash
python3 90_Engine/retriever.py \
  --db examples/mini-vault/fixture.db \
  --vault-root examples/mini-vault \
  --query "How should uncertain agent memory be handled?" \
  --include-reviews
```

## Expected Retrieval Behavior

Example query:

```text
How should uncertain agent memory be handled?
```

Expected relevant nodes:

- `70_Contradictions/Agent Memory Retrieval Weighting.md`
- `80_Reviews/Needs Human Review.md`
- `20_Concepts/Agent Memory.md`
- `20_Concepts/Human Review Queue.md`
- `40_Decisions/2026-06-01-route-uncertain-memory-to-review-queue.md`

The important property is not only rank. Results should expose layer, status,
confidence, annotation, and score metadata so an agent can distinguish durable
knowledge from unresolved review items. BM25-only fallback may rank small-demo
nodes differently from an embedded vault; the safety invariant is that the
returned context carries the layer and review-state metadata an agent needs.

Representative JSON metadata excerpt:

```json
{
  "nodes": [
    {
      "title": "Agent Memory Retrieval Weighting",
      "layer": "70_Contradictions",
      "type": "contradiction",
      "confidence": "medium",
      "status": "open",
      "annotation": "contradiction / unresolved",
      "score": 7.0993
    },
    {
      "title": "Needs Human Review",
      "layer": "80_Reviews",
      "type": "review",
      "confidence": "high",
      "status": "active",
      "annotation": "low-confidence / possible hallucination",
      "score": 4.08
    },
    {
      "title": "Human Review Queue",
      "layer": "20_Concepts",
      "type": "Concept",
      "confidence": "high",
      "status": "evergreen",
      "annotation": "durable concept",
      "score": 2.4565
    },
    {
      "title": "Agent Memory",
      "layer": "20_Concepts",
      "type": "Concept",
      "confidence": "medium",
      "status": "evergreen",
      "annotation": "durable concept",
      "score": 2.4565
    },
    {
      "title": "2026-06-01-route-uncertain-memory-to-review-queue",
      "layer": "40_Decisions",
      "type": "decision",
      "confidence": "high",
      "status": "active",
      "annotation": "decision record",
      "score": 1.938
    }
  ]
}
```

For contradiction-oriented work, include review/meta layers explicitly:

```bash
python3 90_Engine/retriever.py \
  --db examples/mini-vault/fixture.db \
  --vault-root examples/mini-vault \
  --query "When should unresolved contradictions be included in retrieval?" \
  --include-reviews
```

## Run Eval

```bash
python3 90_Engine/eval_retrieval.py
```

`eval_retrieval.py` defaults to this mini-vault fixture. For a real vault, pass
`--vault-root . --queries <real>.json --db 90_Engine/ltm_cache.db`.
Queries that need unresolved review/meta layers can set `include_reviews: true`
in the query file.
