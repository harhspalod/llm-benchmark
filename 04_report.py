"""
04_report.py
=============
Reads summary.json + results_scored.json and produces:
  - A detailed comparison printed to terminal
  - results_scored.csv       — flat CSV for Excel / Google Sheets
  - report_charts.png        — 4-panel comparison chart
  - final_report.md          — Markdown report you can share with your internship team

Run:
    python 04_report.py
"""

import json
import csv
import os

# Optional imports — charts only
try:
    import matplotlib
    matplotlib.use("Agg")   # non-interactive backend for macOS
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("⚠️  matplotlib / numpy not installed — charts will be skipped.")
    print("    Run:  pip install matplotlib numpy")

SCORED_PATH  = "results_scored.json"
SUMMARY_PATH = "summary.json"
CSV_PATH     = "results_scored.csv"
CHART_PATH   = "report_charts.png"
REPORT_PATH  = "final_report.md"

MODEL_COLORS = {
    "sqlcoder":       "#4361EE",
    "codellama":      "#F72585",
    "deepseek-coder": "#4CC9F0",
}

METRIC_LABELS = {
    "valid_sql":       "Valid SQL %",
    "exact_match":     "Exact Match %",
    "exec_score":      "Execution Accuracy %",
    "bleu":            "BLEU Score",
    "component_score": "Component Match %",
}


# ══════════════════════════════════════════════════════════════
# 1. Export CSV
# ══════════════════════════════════════════════════════════════

def export_csv():
    with open(SCORED_PATH) as f:
        records = json.load(f)

    fieldnames = [
        "model", "question_id", "difficulty", "question",
        "valid_sql", "exact_match", "exec_score", "exec_match",
        "bleu", "component_score",
        "pred_rows", "gold_rows", "pred_error",
        "latency_sec", "tokens_per_sec",
        "predicted_sql", "gold_sql",
    ]

    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in records:
            row = {
                "model":           r["model"],
                "question_id":     r["question_id"],
                "difficulty":      r["difficulty"],
                "question":        r["question"],
                "latency_sec":     r.get("latency_sec", ""),
                "tokens_per_sec":  r.get("tokens_per_sec", ""),
                "predicted_sql":   r.get("predicted_sql", ""),
                "gold_sql":        r.get("gold_sql", ""),
                **{k: r["metrics"].get(k, "") for k in
                   ["valid_sql","exact_match","exec_score","exec_match",
                    "bleu","component_score","pred_rows","gold_rows","pred_error"]},
            }
            writer.writerow(row)

    print(f"✅  CSV exported → {CSV_PATH}")


# ══════════════════════════════════════════════════════════════
# 2. Charts
# ══════════════════════════════════════════════════════════════

def make_charts(summary: dict):
    if not HAS_MPL:
        return

    per_model = summary["per_model"]
    per_diff  = summary["per_model_per_difficulty"]

    model_names = list(per_model.keys())
    short_names = [m.split(":")[0] for m in model_names]
    colors      = [MODEL_COLORS.get(s, "#888") for s in short_names]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("SQL LLM Evaluation — Finance Domain", fontsize=16, fontweight="bold", y=0.98)
    fig.patch.set_facecolor("#F8F9FA")

    def bar_group(ax, metric, title, pct=True):
        vals = [per_model[m].get(metric, 0) * (100 if pct else 1) for m in model_names]
        bars = ax.bar(short_names, vals, color=colors, edgecolor="white", linewidth=1.5, width=0.5)
        ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
        ax.set_ylim(0, 110 if pct else max(vals) * 1.25 + 0.01)
        ax.set_facecolor("#FFFFFF")
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="x", labelsize=10)
        for bar, val in zip(bars, vals):
            label = f"{val:.1f}{'%' if pct else ''}"
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + (1.5 if pct else 0.005),
                    label, ha="center", va="bottom", fontsize=10, fontweight="bold")

    # Panel 1 — Core metrics grouped bar
    ax = axes[0, 0]
    core_metrics = ["valid_sql", "exact_match", "exec_score", "component_score"]
    core_labels  = ["Valid SQL", "Exact Match", "Exec Acc", "Comp Match"]
    n_metrics = len(core_metrics)
    n_models  = len(model_names)
    x         = np.arange(n_metrics)
    width     = 0.22

    for i, (model, sname, color) in enumerate(zip(model_names, short_names, colors)):
        vals = [per_model[model].get(m, 0) * 100 for m in core_metrics]
        offset = (i - n_models / 2 + 0.5) * width
        bars = ax.bar(x + offset, vals, width, label=sname, color=color,
                      edgecolor="white", linewidth=1)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.8,
                    f"{val:.0f}", ha="center", va="bottom", fontsize=7.5)

    ax.set_xticks(x)
    ax.set_xticklabels(core_labels, fontsize=10)
    ax.set_ylim(0, 115)
    ax.set_title("Core Metrics Comparison (%)", fontsize=12, fontweight="bold", pad=10)
    ax.set_facecolor("#FFFFFF")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=9)

    # Panel 2 — Execution accuracy by difficulty
    ax = axes[0, 1]
    difficulties = ["easy", "medium", "hard"]
    x = np.arange(len(difficulties))
    width = 0.22

    for i, (model, sname, color) in enumerate(zip(model_names, short_names, colors)):
        vals = []
        for d in difficulties:
            v = per_diff.get(model, {}).get(d, {}).get("exec_score", 0) * 100
            vals.append(v)
        offset = (i - n_models / 2 + 0.5) * width
        bars = ax.bar(x + offset, vals, width, label=sname, color=color,
                      edgecolor="white", linewidth=1)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.8,
                    f"{val:.0f}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels([d.capitalize() for d in difficulties], fontsize=10)
    ax.set_ylim(0, 115)
    ax.set_title("Execution Accuracy by Difficulty (%)", fontsize=12, fontweight="bold", pad=10)
    ax.set_facecolor("#FFFFFF")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=9)

    # Panel 3 — Latency
    ax = axes[1, 0]
    bar_group(ax, "avg_latency_sec", "Average Latency per Query (seconds)", pct=False)
    ax.set_ylabel("Seconds", fontsize=10)

    # Panel 4 — BLEU Score
    ax = axes[1, 1]
    bar_group(ax, "bleu", "BLEU Score (higher = more similar to gold SQL)", pct=False)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("BLEU", fontsize=10)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(CHART_PATH, dpi=150, bbox_inches="tight", facecolor="#F8F9FA")
    plt.close()
    print(f"✅  Charts saved → {CHART_PATH}")


# ══════════════════════════════════════════════════════════════
# 3. Markdown Report
# ══════════════════════════════════════════════════════════════

def make_report(summary: dict, scored: list):
    per_model = summary["per_model"]
    per_diff  = summary["per_model_per_difficulty"]
    model_names = list(per_model.keys())

    # Determine winner per metric
    def best(metric, higher=True):
        vals = {m: per_model[m].get(metric, 0) for m in model_names}
        return max(vals, key=vals.get) if higher else min(vals, key=vals.get)

    winner_exec  = best("exec_score")
    winner_em    = best("exact_match")
    winner_speed = best("avg_latency_sec", higher=False)
    winner_comp  = best("component_score")

    # Overall winner: weighted score
    weights = {"exec_score": 0.40, "exact_match": 0.25,
               "component_score": 0.20, "bleu": 0.10, "valid_sql": 0.05}
    weighted = {}
    for m in model_names:
        s = sum(per_model[m].get(k, 0) * w for k, w in weights.items())
        weighted[m] = round(s, 4)
    overall_winner = max(weighted, key=weighted.get)

    # Error analysis — most common failures
    failures = [r for r in scored if not r["metrics"]["exec_match"]]
    fail_by_diff = {}
    for d in ["easy", "medium", "hard"]:
        n_fail = sum(1 for r in failures if r["difficulty"] == d)
        n_total = sum(1 for r in scored if r["difficulty"] == d)
        fail_by_diff[d] = (n_fail, n_total)

    lines = []
    lines.append("# SQL LLM Evaluation Report — Finance Domain\n")
    lines.append(f"**Models tested:** {', '.join(m.split(':')[0] for m in model_names)}  ")
    lines.append(f"**Questions:** 40 (10 easy · 14 medium · 16 hard)  ")
    lines.append(f"**Database:** finance.db (SQLite, 6 tables)  \n")

    lines.append("---\n")
    lines.append("## Overall Results\n")

    # Summary table
    header = "| Model | Valid SQL | Exact Match | Exec Accuracy | BLEU | Comp Match | Latency | tok/s |"
    sep    = "|-------|-----------|-------------|---------------|------|------------|---------|-------|"
    lines.append(header)
    lines.append(sep)
    for m in model_names:
        s = per_model[m]
        name = m.split(":")[0]
        medal = " 🏆" if m == overall_winner else ""
        lines.append(
            f"| **{name}**{medal} "
            f"| {s.get('valid_sql',0)*100:.1f}% "
            f"| {s.get('exact_match',0)*100:.1f}% "
            f"| {s.get('exec_score',0)*100:.1f}% "
            f"| {s.get('bleu',0):.3f} "
            f"| {s.get('component_score',0)*100:.1f}% "
            f"| {s.get('avg_latency_sec',0):.2f}s "
            f"| {s.get('avg_tokens_per_sec',0):.1f} |"
        )
    lines.append("")

    lines.append("---\n")
    lines.append("## Execution Accuracy by Difficulty\n")

    header2 = "| Model | Easy | Medium | Hard |"
    sep2    = "|-------|------|--------|------|"
    lines.append(header2)
    lines.append(sep2)
    for m in model_names:
        name = m.split(":")[0]
        row = f"| **{name}** "
        for d in ["easy", "medium", "hard"]:
            v = per_diff.get(m, {}).get(d, {}).get("exec_score", 0)
            row += f"| {v*100:.1f}% "
        row += "|"
        lines.append(row)
    lines.append("")

    lines.append("---\n")
    lines.append("## Metric Winners\n")
    lines.append(f"- 🥇 **Execution Accuracy**: `{winner_exec.split(':')[0]}`")
    lines.append(f"- 🥇 **Exact Match**: `{winner_em.split(':')[0]}`")
    lines.append(f"- ⚡ **Fastest (lowest latency)**: `{winner_speed.split(':')[0]}`")
    lines.append(f"- 🧩 **Component Match**: `{winner_comp.split(':')[0]}`")
    lines.append("")

    lines.append("---\n")
    lines.append("## Weighted Score (Ranking)\n")
    lines.append("Weights: Exec Accuracy 40% · Exact Match 25% · Component Match 20% · BLEU 10% · Valid SQL 5%\n")
    for rank, (m, score) in enumerate(sorted(weighted.items(), key=lambda x: -x[1]), 1):
        medal = ["🥇", "🥈", "🥉"][rank - 1] if rank <= 3 else f"{rank}."
        lines.append(f"{medal} **{m.split(':')[0]}** — {score:.4f}")
    lines.append("")

    lines.append("---\n")
    lines.append("## Error Analysis\n")
    lines.append("| Difficulty | Failed | Total | Failure Rate |")
    lines.append("|------------|--------|-------|--------------|")
    for d, (nf, nt) in fail_by_diff.items():
        lines.append(f"| {d.capitalize()} | {nf} | {nt} | {nf/nt*100 if nt else 0:.1f}% |")
    lines.append("")

    lines.append("---\n")
    lines.append("## Sample Failures (Exec Accuracy = 0)\n")
    shown = 0
    for r in scored:
        if r["metrics"]["exec_score"] == 0 and shown < 3:
            name = r["model"].split(":")[0]
            lines.append(f"### Q{r['question_id']} ({r['difficulty']}) — {name}")
            lines.append(f"**Question:** {r['question']}")
            lines.append(f"```sql\n-- Gold SQL\n{r['gold_sql']}\n```")
            lines.append(f"```sql\n-- Predicted SQL\n{r.get('predicted_sql','(empty)')}\n```")
            lines.append(f"**Error:** {r['metrics'].get('pred_error', 'wrong result')}\n")
            shown += 1

    lines.append("---\n")
    lines.append("## Recommendation\n")
    winner_short = overall_winner.split(":")[0]
    lines.append(
        f"Based on quantitative evaluation across 6 metrics on 40 finance-domain "
        f"SQL questions, **`{winner_short}`** is the best-performing local LLM for "
        f"SQL query generation with a weighted score of **{weighted[overall_winner]:.4f}**.\n"
    )
    lines.append("### Key takeaways")
    lines.append("- Execution Accuracy is the most reliable metric — it tests actual correctness, not just text similarity.")
    lines.append("- Hard queries (multi-join, subqueries, window functions) reveal the biggest gaps between models.")
    lines.append("- BLEU can be misleading — a model can produce wrong SQL that looks textually similar.")
    lines.append("- For production use, prioritize Execution Accuracy + Component Match over Exact Match.")
    lines.append("")
    lines.append("---")
    lines.append("*Generated by sql-llm-eval pipeline | Finance DB | SQLite*")

    with open(REPORT_PATH, "w") as f:
        f.write("\n".join(lines))
    print(f"✅  Markdown report → {REPORT_PATH}")


# ══════════════════════════════════════════════════════════════
# 4. Terminal summary
# ══════════════════════════════════════════════════════════════

def print_terminal_summary(summary: dict):
    per_model = summary["per_model"]
    model_names = list(per_model.keys())

    print("\n" + "=" * 70)
    print("  FINAL RESULTS SUMMARY")
    print("=" * 70)
    print(f"  {'Model':<22} {'Valid':>5} {'EM':>5} {'Exec':>6} {'BLEU':>6} {'Comp':>6} {'Lat':>6}")
    print("-" * 70)
    for m in model_names:
        s = per_model[m]
        name = m.split(":")[0]
        print(f"  {name:<22} "
              f"{s.get('valid_sql',0)*100:>4.0f}%  "
              f"{s.get('exact_match',0)*100:>4.0f}%  "
              f"{s.get('exec_score',0)*100:>5.0f}%  "
              f"{s.get('bleu',0):>5.3f}  "
              f"{s.get('component_score',0)*100:>5.0f}%  "
              f"{s.get('avg_latency_sec',0):>5.2f}s")
    print("=" * 70)

    # Per difficulty breakdown
    print("\n  EXEC ACCURACY BY DIFFICULTY")
    print("-" * 50)
    print(f"  {'Model':<22} {'Easy':>6} {'Medium':>8} {'Hard':>6}")
    print("-" * 50)
    per_diff = summary["per_model_per_difficulty"]
    for m in model_names:
        name = m.split(":")[0]
        easy   = per_diff.get(m, {}).get("easy",   {}).get("exec_score", 0) * 100
        medium = per_diff.get(m, {}).get("medium", {}).get("exec_score", 0) * 100
        hard   = per_diff.get(m, {}).get("hard",   {}).get("exec_score", 0) * 100
        print(f"  {name:<22} {easy:>5.0f}%  {medium:>7.0f}%  {hard:>5.0f}%")
    print("=" * 50)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Check inputs exist
    for path in [SCORED_PATH, SUMMARY_PATH]:
        if not os.path.exists(path):
            print(f"❌  {path} not found. Run 03_metrics.py first.")
            exit(1)

    with open(SUMMARY_PATH) as f:
        summary = json.load(f)
    with open(SCORED_PATH) as f:
        scored = json.load(f)

    print_terminal_summary(summary)
    export_csv()
    make_charts(summary)
    make_report(summary, scored)

    print("\n✅  All outputs ready:")
    print(f"    📊  {CHART_PATH}")
    print(f"    📄  {REPORT_PATH}")
    print(f"    📋  {CSV_PATH}")
    print("\n🎉  Evaluation complete! Open final_report.md for your internship writeup.")