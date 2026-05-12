"""
01_split.py — Read CSV, inspect it, then split into train/val/test
"""

import json
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split

CSV_PATH    = "dataset.csv"   # <-- put your CSV here, same folder as this script
TRAIN_RATIO = 0.80
VAL_RATIO   = 0.10
TEST_RATIO  = 0.10
SEED        = 42

# ── 1. Load ───────────────────────────────────────────────────────────────────
df = pd.read_csv(CSV_PATH)

print("=" * 60)
print("STEP 1 — RAW DATA INSPECTION")
print("=" * 60)
print(f"  Total rows   : {len(df)}")
print(f"  Columns      : {list(df.columns)}")
print(f"  Nulls        : {df.isnull().sum().to_dict()}")
print()

# ── 2. Validate columns ───────────────────────────────────────────────────────
required = ["structured_input", "sql", "sql_type"]
missing  = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns: {missing}")
print("  ✅ All required columns present")
print()

# ── 3. Show sql_type distribution ─────────────────────────────────────────────
print("SQL TYPE DISTRIBUTION (full dataset):")
counts = df["sql_type"].value_counts()
for t, n in counts.items():
    bar = "█" * min(n, 50)   # cap bar at 50 chars for large datasets
    print(f"  {t:<12} {n:>6}  {bar}")
print()

# ── 4. Clean ──────────────────────────────────────────────────────────────────
before = len(df)
df = df.dropna(subset=required)
df["structured_input"] = df["structured_input"].astype(str).str.strip()
df["sql"]              = df["sql"].astype(str).str.strip()
df["sql_type"]         = df["sql_type"].astype(str).str.strip().str.upper()
df = df[df["structured_input"].str.len() > 0]
df = df[df["sql"].str.len() > 0]
df = df.reset_index(drop=True)
print(f"  Rows after cleaning: {len(df)}  (dropped {before - len(df)})")
print()

# ── 5. Handle rare classes (need ≥ 3 samples for stratified split) ────────────
type_counts = df["sql_type"].value_counts()
rare = type_counts[type_counts < 3].index.tolist()
if rare:
    print(f"  ⚠️  Rare sql_types (< 3 samples) merged → 'OTHER': {rare}")
    df.loc[df["sql_type"].isin(rare), "sql_type"] = "OTHER"
else:
    print("  ✅ No rare sql_types")
print()

# ── 6. Stratified split ───────────────────────────────────────────────────────
def safe_split(data, test_size, seed, label=""):
    """Try stratified split; fall back to random if any class too small."""
    try:
        return train_test_split(
            data, test_size=test_size,
            stratify=data["sql_type"], random_state=seed
        )
    except ValueError as e:
        print(f"  ⚠️  Stratified split not possible ({label}): falling back to random")
        return train_test_split(data, test_size=test_size, random_state=seed)

train_df, temp_df = safe_split(df, VAL_RATIO + TEST_RATIO, SEED, "train/temp")
relative_test = TEST_RATIO / (VAL_RATIO + TEST_RATIO)
val_df, test_df = safe_split(temp_df, relative_test, SEED, "val/test")

print("SPLIT RESULT:")
print(f"  Train : {len(train_df):>6} rows  ({len(train_df)/len(df):.0%})")
print(f"  Val   : {len(val_df):>6} rows  ({len(val_df)/len(df):.0%})")
print(f"  Test  : {len(test_df):>6} rows  ({len(test_df)/len(df):.0%})")
print()

# ── 7. Per-split type breakdown ───────────────────────────────────────────────
all_types = sorted(df["sql_type"].unique())
print(f"  {'SQL TYPE':<12} {'TRAIN':>7} {'VAL':>7} {'TEST':>7}")
print("  " + "-" * 36)
for t in all_types:
    tr = (train_df["sql_type"] == t).sum()
    va = (val_df["sql_type"]   == t).sum()
    te = (test_df["sql_type"]  == t).sum()
    print(f"  {t:<12} {tr:>7} {va:>7} {te:>7}")
print()

# ── 8. SQLCoder prompt format ─────────────────────────────────────────────────
TRAIN_TEMPLATE = (
    "### Task\n"
    "Generate a SQL query to answer the following question.\n\n"
    "### Input\n{structured_input}\n\n"
    "### Response\n{sql}"
)
INFER_TEMPLATE = (
    "### Task\n"
    "Generate a SQL query to answer the following question.\n\n"
    "### Input\n{structured_input}\n\n"
    "### Response\n"
)

def to_record(row, for_inference=False):
    tmpl = INFER_TEMPLATE if for_inference else TRAIN_TEMPLATE
    return {
        "text":             tmpl.format(**row),
        "sql":              row["sql"],
        "sql_type":         row["sql_type"],
        "structured_input": row["structured_input"],
    }

# ── 9. Write JSONL files ──────────────────────────────────────────────────────
def write_jsonl(records, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  Wrote {len(records):>6} records → {path}")

write_jsonl([to_record(r)                     for r in train_df.to_dict("records")], "data/train.jsonl")
write_jsonl([to_record(r)                     for r in val_df.to_dict("records")],   "data/val.jsonl")
write_jsonl([to_record(r)                     for r in test_df.to_dict("records")],  "data/test.jsonl")
write_jsonl([to_record(r, for_inference=True) for r in test_df.to_dict("records")],  "data/test_inference.jsonl")
print()

# ── 10. Sample prompt preview ─────────────────────────────────────────────────
print("SAMPLE TRAINING PROMPT (first train row):")
print("-" * 60)
print(to_record(train_df.iloc[0].to_dict())["text"])
print("-" * 60)
print()
print("✅ Split complete — paste your output here, then we do step 2.")