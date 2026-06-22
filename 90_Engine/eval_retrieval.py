#!/usr/bin/env python3
"""
90_Engine/eval_retrieval.py
Retrieval evaluation scaffold — 검색 "품질"이 기대와 맞는지 평가한다.

이 스크립트는 "코드가 동작한다"가 아니라 **"검색 결과가 기대(ground truth)와
맞는가"**를 측정한다. Retrieval Policy(00_System/Retrieval Policy.yaml)의 가중치는
잠정적 사전값(provisional prior)이므로, 이 도구로 측정하며 조정한다.

측정 지표:
  - MRR@k              : 기대 노드 중 첫 적중의 평균 역순위 (랭킹 품질)
  - Recall@k           : top-k 안에 들어온 기대 노드 비율 (커버리지)
  - review_leakage_rate: review opt-in이 아닌 쿼리의 top-k 중 검토/메타 계층
                         (60/70/80) 비율 (필터 누수)
  - raw_overexposure_rate: review opt-in이 아닌 쿼리의 top-k 중 06_Raw 비율
                           (원본 과다노출)

기본 스코프(include_reviews=False)에서는 review_leakage_rate가 0이어야 한다.

사용:
    python3 eval_retrieval.py --db 90_Engine/ltm_cache.db --queries eval_queries.sample.json
    python3 eval_retrieval.py --db ... --queries my.json --top-k 5 \
            --policy "00_System/Retrieval Policy.yaml" \
            --max-review-leakage 0.0 --max-raw-overexposure 0.6

queries 파일(JSON):
    {
      "queries": [
        {"query": "왜 LLM은 strawberry의 r 개수를 못 세나?",
         "expected": ["Byte Pair Encoding", "Tokenizer", "Glitch Tokens"]},
        {"query": "When should unresolved contradictions be included in retrieval?",
         "expected": ["Agent Memory Retrieval Weighting"],
         "include_reviews": true}
      ]
    }
(.yaml도 PyYAML 설치 시 지원. expected는 top-k에 떠야 하는 node 제목(stem) 목록.)
"""

import os
import sys
import json
import argparse
from pathlib import Path

# 검토/메타·원본 계층 식별 (retriever와 동일 기준; import는 main에서 lazy)
REVIEW_LAYERS = ("60_Open_Questions", "70_Contradictions", "80_Reviews")
RAW_LAYER = "06_Raw"


# ─────────────────────────────────────────────────────────────
# 순수 지표 함수 (retriever/duckdb 불필요 → 단위 테스트 가능)
# ─────────────────────────────────────────────────────────────
def reciprocal_rank(ranked_titles, expected, k):
    exp = set(expected)
    for i, t in enumerate(ranked_titles[:k], 1):
        if t in exp:
            return 1.0 / i
    return 0.0


def recall_at_k(ranked_titles, expected, k):
    exp = set(expected)
    if not exp:
        return None
    hit = sum(1 for t in set(ranked_titles[:k]) if t in exp)
    return hit / len(exp)


def evaluate(per_query_nodes, queries, k, reviews_allowed_default=False,
             review_layers=REVIEW_LAYERS, raw_layer=RAW_LAYER):
    """per_query_nodes: 쿼리별 결과 노드 리스트 [[{title, layer}, ...], ...].
    queries: [{query, expected}]. 반환: 집계 지표 + 쿼리별 상세."""
    rr_list, recall_list = [], []
    leakage_total_results = leaked = raw_hits = 0
    per_query = []
    for nodes, q in zip(per_query_nodes, queries):
        topk = nodes[:k]
        titles = [n.get("title") for n in topk]
        expected = q.get("expected") or []
        rr = reciprocal_rank(titles, expected, k)
        rec = recall_at_k(titles, expected, k)
        if expected:
            rr_list.append(rr)
            recall_list.append(rec)
        reviews_allowed = bool(q.get("include_reviews", reviews_allowed_default))
        if not reviews_allowed:
            leakage_total_results += len(topk)
            leaked += sum(1 for n in topk if n.get("layer") in review_layers)
            raw_hits += sum(1 for n in topk if n.get("layer") == raw_layer)
        per_query.append({
            "query": q.get("query"),
            "expected": expected,
            "got": titles,
            "include_reviews": reviews_allowed,
            "rr": round(rr, 4),
            "recall": (round(rec, 4) if rec is not None else None),
        })

    def mean(xs):
        return (sum(xs) / len(xs)) if xs else 0.0

    return {
        "k": k,
        "n_queries": len(queries),
        "n_scored": len(rr_list),
        "mrr_at_k": round(mean(rr_list), 4),
        "recall_at_k": round(mean(recall_list), 4),
        "review_leakage_rate": round(leaked / leakage_total_results, 4) if leakage_total_results else 0.0,
        "raw_overexposure_rate": round(raw_hits / leakage_total_results, 4) if leakage_total_results else 0.0,
        "per_query": per_query,
    }


# ─────────────────────────────────────────────────────────────
# I/O
# ─────────────────────────────────────────────────────────────
def load_queries(path):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError:
            sys.exit("ERROR: .yaml queries에는 PyYAML 필요. pip install pyyaml "
                     "또는 .json 사용.")
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    queries = data.get("queries") if isinstance(data, dict) else data
    if not queries:
        sys.exit("ERROR: queries 파일에 'queries' 항목이 없습니다.")
    return queries


def run_eval(retriever, queries, k=5, max_hops=2,
             include_raw=True, include_reviews=False):
    """retriever.retrieve를 쿼리마다 호출해 결과 노드 리스트를 모은다."""
    per_query_nodes = []
    for q in queries:
        query_include_raw = q.get("include_raw", include_raw)
        query_include_reviews = q.get("include_reviews", include_reviews)
        res = retriever.retrieve(
            q["query"], top_k=k, max_hops=max_hops, max_nodes=k,
            include_raw=query_include_raw, include_reviews=query_include_reviews,
        )
        per_query_nodes.append(res["layer1_meta"]["nodes"])
    return per_query_nodes


def print_report(metrics, thresholds):
    print()
    print("=" * 64)
    print("  Retrieval Evaluation (검색 품질)")
    print("=" * 64)
    print(f"  queries: {metrics['n_queries']} (scored: {metrics['n_scored']}) | k={metrics['k']}")
    print(f"  MRR@{metrics['k']}              : {metrics['mrr_at_k']}")
    print(f"  Recall@{metrics['k']}           : {metrics['recall_at_k']}")
    print(f"  review_leakage_rate    : {metrics['review_leakage_rate']}  (목표 ≤ {thresholds['max_review_leakage']})")
    print(f"  raw_overexposure_rate  : {metrics['raw_overexposure_rate']}  (목표 ≤ {thresholds['max_raw_overexposure']})")
    print("-" * 64)
    for pq in metrics["per_query"]:
        mark = "✓" if pq["rr"] > 0 else "✗"
        scope = " include_reviews" if pq.get("include_reviews") else ""
        print(f"  {mark} rr={pq['rr']:.3f} recall={pq['recall']}{scope}  «{pq['query']}»")
        print(f"      expected: {pq['expected']}")
        print(f"      got     : {pq['got']}")
    print("=" * 64)


def check_thresholds(metrics, thresholds):
    """하드 임계 위반 목록 반환(비면 통과)."""
    fails = []
    if metrics["review_leakage_rate"] > thresholds["max_review_leakage"]:
        fails.append(f"review_leakage_rate {metrics['review_leakage_rate']} > {thresholds['max_review_leakage']}")
    if metrics["raw_overexposure_rate"] > thresholds["max_raw_overexposure"]:
        fails.append(f"raw_overexposure_rate {metrics['raw_overexposure_rate']} > {thresholds['max_raw_overexposure']}")
    if thresholds["min_mrr"] and metrics["mrr_at_k"] < thresholds["min_mrr"]:
        fails.append(f"mrr_at_k {metrics['mrr_at_k']} < {thresholds['min_mrr']}")
    if thresholds["min_recall"] and metrics["recall_at_k"] < thresholds["min_recall"]:
        fails.append(f"recall_at_k {metrics['recall_at_k']} < {thresholds['min_recall']}")
    return fails


def main():
    ap = argparse.ArgumentParser(description="Retrieval quality evaluation")
    # 기본값은 재현 가능한 데모 픽스처(examples/mini-vault)를 가리킨다. 실제 vault를
    # 평가하려면 --vault-root . --db 90_Engine/ltm_cache.db --queries <real>.json 로 덮어쓴다.
    ap.add_argument("--db", default="examples/mini-vault/fixture.db")
    ap.add_argument("--queries", default="examples/mini-vault/eval_queries.json")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--hops", type=int, default=2)
    ap.add_argument("--policy", default=None, help="Retrieval Policy 파일 override")
    ap.add_argument("--vault-root", default="examples/mini-vault")
    ap.add_argument("--ollama-url", default="http://localhost:11434")
    ap.add_argument("--ollama-model", default="bge-m3")
    ap.add_argument("--include-reviews", action="store_true")
    ap.add_argument("--no-raw", action="store_true")
    ap.add_argument("--max-review-leakage", type=float, default=0.0)
    ap.add_argument("--max-raw-overexposure", type=float, default=0.6)
    ap.add_argument("--min-mrr", type=float, default=0.0)
    ap.add_argument("--min-recall", type=float, default=0.0)
    ap.add_argument("--json-only", action="store_true")
    args = ap.parse_args()

    queries = load_queries(args.queries)

    # retriever는 duckdb를 요구하므로 여기서 lazy import
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import retriever as rt
    r = rt.Retriever(args.db, args.ollama_url, args.ollama_model,
                     vault_root=args.vault_root, policy_path=args.policy)

    per_query_nodes = run_eval(
        r, queries, k=args.top_k, max_hops=args.hops,
        include_raw=not args.no_raw, include_reviews=args.include_reviews,
    )
    metrics = evaluate(per_query_nodes, queries, args.top_k,
                       reviews_allowed_default=args.include_reviews)
    thresholds = {
        "max_review_leakage": args.max_review_leakage,
        "max_raw_overexposure": args.max_raw_overexposure,
        "min_mrr": args.min_mrr,
        "min_recall": args.min_recall,
    }

    if args.json_only:
        print(json.dumps({"metrics": {k: v for k, v in metrics.items() if k != "per_query"},
                          "per_query": metrics["per_query"]}, ensure_ascii=False, indent=2))
    else:
        print_report(metrics, thresholds)

    fails = check_thresholds(metrics, thresholds)
    if fails:
        print("\n[FAIL] 품질 임계 위반:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("\n[OK] 모든 임계 통과.")


if __name__ == "__main__":
    main()
