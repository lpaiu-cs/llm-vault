# examples/mini-vault — demo corpus and eval fixture

This folder is a small, non-private vault that shows how `llm-vault` separates
raw evidence, source summaries, concepts, project dashboards, decision records,
and review items.

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

## Run Eval

```bash
python3 90_Engine/eval_retrieval.py
```

`eval_retrieval.py` defaults to this mini-vault fixture. For a real vault, pass
`--vault-root . --queries <real>.json --db 90_Engine/ltm_cache.db`.
