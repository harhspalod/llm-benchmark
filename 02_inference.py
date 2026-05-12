"""
02_inference.py
================
Sends every question in dataset.json to each local LLM via Ollama.
Captures the generated SQL, latency, and token stats.

Run:
    python 02_inference.py
Output:
    results_raw.json  — all model responses with metadata
"""

import json
import time
import re
import requests

DATASET_PATH  = "dataset.json"
OUTPUT_PATH   = "results_raw.json"
OLLAMA_URL    = "http://localhost:11434/api/generate"

MODELS = [
    "sqlcoder:7b",
    "codellama:7b",
    "deepseek-coder:6.7b",
]

# ──────────────────────────────────────────────────────────────
# Prompt builder — each model has a preferred prompt style
# ──────────────────────────────────────────────────────────────

SCHEMA_CONTEXT = """
You are an expert SQL assistant for a finance database.

Database schema:
- customers(customer_id, name, email, country, segment, created_at)
- accounts(account_id, customer_id, account_type, balance, currency, opened_at, status)
- transactions(txn_id, account_id, txn_type, amount, category, description, txn_date)
- loans(loan_id, customer_id, loan_type, principal, interest_rate, tenure_months, disbursed_at, status)
- investments(inv_id, account_id, asset_type, symbol, quantity, purchase_price, current_price, purchased_at)
- branches(branch_id, branch_name, city, country, manager_name)

Enums:
- customers.segment: retail, corporate, premium
- accounts.account_type: savings, checking, investment, loan
- accounts.status: active, closed, frozen
- transactions.txn_type: credit, debit
- loans.loan_type: personal, mortgage, auto, business
- loans.status: active, closed, defaulted
- investments.asset_type: stock, bond, mutual_fund, etf, crypto
""".strip()


def build_prompt(model_name: str, question: str) -> str:
    """Build a model-specific prompt. SQLCoder has a special template."""
    if "sqlcoder" in model_name:
        # SQLCoder's recommended prompt format
        return (
            f"### Task\nGenerate a SQL query to answer this question:\n`{question}`\n\n"
            f"### Database Schema\n{SCHEMA_CONTEXT}\n\n"
            "### Answer\nHere is the SQL query that answers the question:\n```sql\n"
        )
    else:
        # Generic instruction format for CodeLlama and DeepSeek-Coder
        return (
            f"{SCHEMA_CONTEXT}\n\n"
            f"Write a single SQLite SQL query to answer the following question.\n"
            f"Return ONLY the SQL query, no explanation.\n\n"
            f"Question: {question}\n\n"
            f"SQL:"
        )


# ──────────────────────────────────────────────────────────────
# SQL extractor — pull clean SQL from messy LLM output
# ──────────────────────────────────────────────────────────────

def extract_sql(raw_text: str) -> str:
    """Extract the first SQL block from model output."""
    # Try fenced code block first
    patterns = [
        r"```sql\s*(.*?)```",
        r"```\s*(SELECT|WITH|INSERT|UPDATE|DELETE.*?)```",
        r"(SELECT\s+.*?;)",
        r"(WITH\s+.*?;)",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw_text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # Fallback: everything after "SQL:" or "Answer:"
    for marker in ["SQL:", "Answer:", "```"]:
        if marker in raw_text:
            return raw_text.split(marker, 1)[-1].strip().rstrip("```").strip()

    return raw_text.strip()


# ──────────────────────────────────────────────────────────────
# Single model query
# ──────────────────────────────────────────────────────────────

def query_model(model: str, prompt: str, timeout: int = 120) -> dict:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,   # deterministic — critical for fair eval
            "num_predict": 512,
            "stop": ["###", "```\n\n", "--\n"],
        }
    }

    start = time.time()
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        latency = round(time.time() - start, 3)

        raw_output  = data.get("response", "")
        sql_output  = extract_sql(raw_output)
        prompt_tok  = data.get("prompt_eval_count", 0)
        gen_tok     = data.get("eval_count", 0)
        tok_per_sec = round(gen_tok / latency, 2) if latency > 0 else 0

        return {
            "success": True,
            "raw_output": raw_output,
            "predicted_sql": sql_output,
            "latency_sec": latency,
            "prompt_tokens": prompt_tok,
            "generated_tokens": gen_tok,
            "tokens_per_sec": tok_per_sec,
            "error": None,
        }

    except requests.exceptions.Timeout:
        return {"success": False, "raw_output": "", "predicted_sql": "",
                "latency_sec": timeout, "error": "TIMEOUT"}
    except Exception as e:
        return {"success": False, "raw_output": "", "predicted_sql": "",
                "latency_sec": round(time.time() - start, 3), "error": str(e)}


# ──────────────────────────────────────────────────────────────
# Main loop
# ──────────────────────────────────────────────────────────────

def run_inference():
    with open(DATASET_PATH) as f:
        dataset = json.load(f)

    all_results = []
    total = len(MODELS) * len(dataset)
    done  = 0

    for model in MODELS:
        print(f"\n{'='*55}")
        print(f"  Model: {model}")
        print(f"{'='*55}")

        for q in dataset:
            done += 1
            prompt = build_prompt(model, q["question"])
            print(f"  [{done}/{total}] Q{q['id']:02d} ({q['difficulty']:<6}) — {q['question'][:55]}...")

            result = query_model(model, prompt)

            record = {
                "model":         model,
                "question_id":   q["id"],
                "difficulty":    q["difficulty"],
                "question":      q["question"],
                "gold_sql":      q["gold_sql"],
                **result,
            }
            all_results.append(record)

            status = "✅" if result["success"] else "❌"
            print(f"         {status}  {result['latency_sec']}s  |  "
                  f"{result.get('tokens_per_sec', 0)} tok/s")

            # Brief preview of extracted SQL
            sql_preview = result["predicted_sql"][:80].replace("\n", " ")
            print(f"         SQL: {sql_preview}...")

        print(f"\n  ✅  {model} done.")

    with open(OUTPUT_PATH, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n✅  All results saved → {OUTPUT_PATH}")
    print(f"    Total records: {len(all_results)}")


if __name__ == "__main__":
    # Quick Ollama connectivity check
    try:
        r = requests.get("http://localhost:11434", timeout=5)
        print("✅  Ollama is running.")
    except Exception:
        print("❌  Ollama is not running. Start it with:  ollama serve")
        exit(1)

    run_inference()