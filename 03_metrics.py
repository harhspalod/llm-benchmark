"""
03_metrics.py
==============
Evaluates every model prediction against gold SQL using 6 metrics:

  1. Valid SQL Rate      — is the output parseable SQL?
  2. Exact Match (EM)   — normalized string match
  3. Execution Accuracy — same result set as gold SQL on finance.db
  4. BLEU Score         — token-level text similarity
  5. Component Match    — SELECT / WHERE / GROUP BY / ORDER BY / JOIN correctness
  6. Avg Latency        — seconds per query

Run:
    python 03_metrics.py
Output:
    results_scored.json   — every record with all metric scores
    summary.json          — per-model & per-difficulty aggregate scores
"""

import json
import sqlite3
import re
import math
from collections import defaultdict

try:
    import sqlglot
    HAS_SQLGLOT = True
except ImportError:
    HAS_SQLGLOT = False
    print("⚠️  sqlglot not installed — component match will be skipped.")
    print("    Run:  pip install sqlglot")

RAW_PATH     = "results_raw.json"
SCORED_PATH  = "results_scored.json"
SUMMARY_PATH = "summary.json"
DB_PATH      = "finance.db"


# ══════════════════════════════════════════════════════════════
# METRIC 1 — Valid SQL
# ══════════════════════════════════════════════════════════════

def is_valid_sql(sql: str) -> bool:
    """Check if string is parseable SQL using sqlglot, fallback to keyword check."""
    if not sql or len(sql.strip()) < 5:
        return False
    if HAS_SQLGLOT:
        try:
            stmts = sqlglot.parse(sql)
            return len(stmts) > 0 and stmts[0] is not None
        except Exception:
            return False
    # Fallback: must contain at least SELECT or WITH
    return bool(re.search(r'\b(SELECT|WITH|INSERT|UPDATE|DELETE)\b', sql, re.I))


# ══════════════════════════════════════════════════════════════
# METRIC 2 — Exact Match (normalized)
# ══════════════════════════════════════════════════════════════

def normalize_sql(sql: str) -> str:
    """Lowercase, collapse whitespace, strip trailing semicolons."""
    sql = sql.lower().strip().rstrip(";")
    sql = re.sub(r'\s+', ' ', sql)
    # Remove comments
    sql = re.sub(r'--[^\n]*', '', sql)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    return sql.strip()


def exact_match(pred: str, gold: str) -> bool:
    return normalize_sql(pred) == normalize_sql(gold)


# ══════════════════════════════════════════════════════════════
# METRIC 3 — Execution Accuracy
# ══════════════════════════════════════════════════════════════

def execute_sql(conn: sqlite3.Connection, sql: str):
    """Run SQL and return sorted result rows, or None on error."""
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        # Sort for order-independent comparison
        return sorted([tuple(str(v) for v in row) for row in rows])
    except Exception:
        return None


def execution_accuracy(pred: str, gold: str, conn: sqlite3.Connection) -> dict:
    """
    Returns:
        score      — 1.0 (exact match), 0.5 (same shape, partial), 0.0 (wrong/error)
        pred_error — error message if pred failed
        exec_match — bool, True if results are identical
    """
    gold_result = execute_sql(conn, gold)
    pred_result = execute_sql(conn, pred)

    if pred_result is None:
        return {"score": 0.0, "exec_match": False,
                "pred_error": "execution_failed", "pred_rows": 0, "gold_rows": len(gold_result or [])}

    if gold_result is None:
        # Gold itself failed (shouldn't happen, but be safe)
        return {"score": 0.0, "exec_match": False,
                "pred_error": "gold_execution_failed", "pred_rows": 0, "gold_rows": 0}

    exact = (pred_result == gold_result)
    # Partial credit: same number of rows and columns
    partial = (
        not exact
        and len(pred_result) == len(gold_result)
        and len(pred_result) > 0
        and len(pred_result[0]) == len(gold_result[0])
    )

    return {
        "score":      1.0 if exact else (0.5 if partial else 0.0),
        "exec_match": exact,
        "pred_error": None,
        "pred_rows":  len(pred_result),
        "gold_rows":  len(gold_result),
    }


# ══════════════════════════════════════════════════════════════
# METRIC 4 — BLEU Score (token-level, no external library)
# ══════════════════════════════════════════════════════════════

def tokenize(text: str) -> list:
    return re.findall(r"[a-z0-9_*]+|[(),;]", text.lower())


def ngrams(tokens: list, n: int) -> dict:
    counts = defaultdict(int)
    for i in range(len(tokens) - n + 1):
        counts[tuple(tokens[i:i+n])] += 1
    return counts


def bleu_score(pred: str, gold: str, max_n: int = 4) -> float:
    pred_tokens = tokenize(pred)
    gold_tokens = tokenize(gold)

    if not pred_tokens:
        return 0.0

    # Brevity penalty
    bp = min(1.0, math.exp(1 - len(gold_tokens) / max(len(pred_tokens), 1)))

    precisions = []
    for n in range(1, max_n + 1):
        pred_ng = ngrams(pred_tokens, n)
        gold_ng = ngrams(gold_tokens, n)
        if not pred_ng:
            precisions.append(0.0)
            continue
        clipped = sum(min(c, gold_ng[ng]) for ng, c in pred_ng.items())
        precisions.append(clipped / sum(pred_ng.values()))

    if any(p == 0 for p in precisions):
        # Smoothing: replace zeros with small value
        precisions = [p if p > 0 else 1e-6 for p in precisions]

    log_avg = sum(math.log(p) for p in precisions) / max_n
    return round(bp * math.exp(log_avg), 4)


# ══════════════════════════════════════════════════════════════
# METRIC 5 — Component Match
# ══════════════════════════════════════════════════════════════

CLAUSE_PATTERNS = {
    "has_select":   r'\bSELECT\b',
    "has_where":    r'\bWHERE\b',
    "has_group_by": r'\bGROUP\s+BY\b',
    "has_order_by": r'\bORDER\s+BY\b',
    "has_having":   r'\bHAVING\b',
    "has_join":     r'\bJOIN\b',
    "has_subquery": r'\(\s*SELECT\b',
    "has_limit":    r'\bLIMIT\b',
    "has_window":   r'\bOVER\s*\(',
    "has_agg":      r'\b(SUM|AVG|COUNT|MAX|MIN)\s*\(',
}


def component_match(pred: str, gold: str) -> dict:
    """
    For each SQL clause/feature, check if gold has it and if pred also has it.
    Returns per-component scores and an overall component_score.
    """
    components = {}
    matches = 0
    total_relevant = 0

    for name, pattern in CLAUSE_PATTERNS.items():
        gold_has = bool(re.search(pattern, gold, re.I))
        pred_has = bool(re.search(pattern, pred, re.I))

        if gold_has:
            total_relevant += 1
            hit = pred_has
            matches += int(hit)
            components[name] = {"gold": True, "pred": pred_has, "match": hit}
        else:
            components[name] = {"gold": False, "pred": pred_has, "match": None}

    overall = round(matches / total_relevant, 4) if total_relevant > 0 else 1.0
    return {"component_score": overall, "components": components,
            "matched": matches, "total_clauses": total_relevant}


# ══════════════════════════════════════════════════════════════
# MAIN — score everything
# ══════════════════════════════════════════════════════════════

def score_all():
    with open(RAW_PATH) as f:
        records = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    scored = []

    print(f"Scoring {len(records)} records...\n")

    for i, rec in enumerate(records):
        pred = rec.get("predicted_sql", "")
        gold = rec["gold_sql"]

        valid   = is_valid_sql(pred)
        em      = exact_match(pred, gold)
        ea      = execution_accuracy(pred, gold, conn)
        bleu    = bleu_score(pred, gold)
        comp    = component_match(pred, gold)

        rec["metrics"] = {
            "valid_sql":         int(valid),
            "exact_match":       int(em),
            "exec_score":        ea["score"],
            "exec_match":        ea["exec_match"],
            "pred_error":        ea["pred_error"],
            "pred_rows":         ea["pred_rows"],
            "gold_rows":         ea["gold_rows"],
            "bleu":              bleu,
            "component_score":   comp["component_score"],
            "components":        comp["components"],
        }
        scored.append(rec)

        # Live progress
        model_short = rec["model"].split(":")[0]
        print(f"  [{i+1:>3}/{len(records)}] {model_short:<18} Q{rec['question_id']:02d} "
              f"({rec['difficulty']:<6})  "
              f"valid={valid}  em={em}  exec={ea['score']:.1f}  "
              f"bleu={bleu:.3f}  comp={comp['component_score']:.2f}")

    conn.close()

    with open(SCORED_PATH, "w") as f:
        json.dump(scored, f, indent=2)
    print(f"\n✅  Scored results → {SCORED_PATH}")

    # ── Build summary ─────────────────────────────────────────
    build_summary(scored)


def build_summary(scored: list):
    """Aggregate metrics per model and per difficulty."""
    from collections import defaultdict

    # Per model
    model_buckets = defaultdict(list)
    for rec in scored:
        model_buckets[rec["model"]].append(rec)

    summary = {"per_model": {}, "per_model_per_difficulty": {}}

    METRIC_KEYS = ["valid_sql", "exact_match", "exec_score", "exec_match",
                   "bleu", "component_score"]

    for model, recs in model_buckets.items():
        # Overall
        summary["per_model"][model] = aggregate_metrics(recs, METRIC_KEYS)

        # Per difficulty
        diff_buckets = defaultdict(list)
        for r in recs:
            diff_buckets[r["difficulty"]].append(r)

        summary["per_model_per_difficulty"][model] = {
            diff: aggregate_metrics(drecs, METRIC_KEYS)
            for diff, drecs in diff_buckets.items()
        }

    # Add latency
    for model, recs in model_buckets.items():
        lats = [r["latency_sec"] for r in recs if r.get("success")]
        summary["per_model"][model]["avg_latency_sec"] = round(
            sum(lats) / len(lats), 3) if lats else 0
        tps  = [r["tokens_per_sec"] for r in recs if r.get("success") and r.get("tokens_per_sec")]
        summary["per_model"][model]["avg_tokens_per_sec"] = round(
            sum(tps) / len(tps), 2) if tps else 0

    with open(SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"✅  Summary saved  → {SUMMARY_PATH}\n")

    # Quick print
    print("=" * 60)
    print(f"{'Model':<25} {'Valid%':>6} {'ExactM':>7} {'ExecAcc':>8} {'BLEU':>6} {'Comp':>6}")
    print("-" * 60)
    for model, stats in summary["per_model"].items():
        name = model.split(":")[0]
        print(f"  {name:<23} "
              f"{stats['valid_sql']*100:>5.1f}%  "
              f"{stats['exact_match']*100:>6.1f}%  "
              f"{stats['exec_score']*100:>7.1f}%  "
              f"{stats['bleu']:>5.3f}  "
              f"{stats['component_score']:>5.3f}")
    print("=" * 60)


def aggregate_metrics(recs: list, keys: list) -> dict:
    result = {}
    for k in keys:
        vals = [r["metrics"][k] for r in recs if k in r.get("metrics", {})]
        result[k] = round(sum(vals) / len(vals), 4) if vals else 0.0
    result["n"] = len(recs)
    return result


if __name__ == "__main__":
    score_all()