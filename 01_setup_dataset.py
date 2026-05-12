"""
01_setup_dataset.py
====================
Creates a realistic Finance SQLite database and 40 NL->SQL test questions
across easy / medium / hard difficulty levels.

Run:
    python 01_setup_dataset.py
Output:
    finance.db       — SQLite database with 6 tables
    dataset.json     — 40 questions with gold SQL + difficulty labels
"""

import sqlite3
import json
import random
from datetime import date, timedelta

DB_PATH = "finance.db"
DATASET_PATH = "dataset.json"

# ─────────────────────────────────────────────
# 1.  BUILD THE DATABASE
# ─────────────────────────────────────────────

def build_database():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
    PRAGMA foreign_keys = ON;

    -- Customers
    CREATE TABLE IF NOT EXISTS customers (
        customer_id   INTEGER PRIMARY KEY,
        name          TEXT    NOT NULL,
        email         TEXT    UNIQUE NOT NULL,
        country       TEXT    NOT NULL,
        segment       TEXT    NOT NULL CHECK(segment IN ('retail','corporate','premium')),
        created_at    DATE    NOT NULL
    );

    -- Accounts (each customer can have multiple)
    CREATE TABLE IF NOT EXISTS accounts (
        account_id    INTEGER PRIMARY KEY,
        customer_id   INTEGER NOT NULL REFERENCES customers(customer_id),
        account_type  TEXT    NOT NULL CHECK(account_type IN ('savings','checking','investment','loan')),
        balance       REAL    NOT NULL DEFAULT 0,
        currency      TEXT    NOT NULL DEFAULT 'USD',
        opened_at     DATE    NOT NULL,
        status        TEXT    NOT NULL DEFAULT 'active' CHECK(status IN ('active','closed','frozen'))
    );

    -- Transactions
    CREATE TABLE IF NOT EXISTS transactions (
        txn_id        INTEGER PRIMARY KEY,
        account_id    INTEGER NOT NULL REFERENCES accounts(account_id),
        txn_type      TEXT    NOT NULL CHECK(txn_type IN ('credit','debit')),
        amount        REAL    NOT NULL,
        category      TEXT    NOT NULL,
        description   TEXT,
        txn_date      DATE    NOT NULL
    );

    -- Loans
    CREATE TABLE IF NOT EXISTS loans (
        loan_id       INTEGER PRIMARY KEY,
        customer_id   INTEGER NOT NULL REFERENCES customers(customer_id),
        loan_type     TEXT    NOT NULL CHECK(loan_type IN ('personal','mortgage','auto','business')),
        principal     REAL    NOT NULL,
        interest_rate REAL    NOT NULL,
        tenure_months INTEGER NOT NULL,
        disbursed_at  DATE    NOT NULL,
        status        TEXT    NOT NULL DEFAULT 'active' CHECK(status IN ('active','closed','defaulted'))
    );

    -- Investments
    CREATE TABLE IF NOT EXISTS investments (
        inv_id        INTEGER PRIMARY KEY,
        account_id    INTEGER NOT NULL REFERENCES accounts(account_id),
        asset_type    TEXT    NOT NULL CHECK(asset_type IN ('stock','bond','mutual_fund','etf','crypto')),
        symbol        TEXT    NOT NULL,
        quantity      REAL    NOT NULL,
        purchase_price REAL   NOT NULL,
        current_price  REAL   NOT NULL,
        purchased_at  DATE    NOT NULL
    );

    -- Branches
    CREATE TABLE IF NOT EXISTS branches (
        branch_id     INTEGER PRIMARY KEY,
        branch_name   TEXT    NOT NULL,
        city          TEXT    NOT NULL,
        country       TEXT    NOT NULL,
        manager_name  TEXT    NOT NULL
    );
    """)

    # ── Seed data ──────────────────────────────
    random.seed(42)

    countries  = ["India", "USA", "UK", "Germany", "Singapore"]
    segments   = ["retail", "corporate", "premium"]
    acc_types  = ["savings", "checking", "investment", "loan"]
    categories = ["salary", "rent", "food", "travel", "utilities", "investment", "loan_payment", "transfer"]
    loan_types = ["personal", "mortgage", "auto", "business"]
    assets     = ["stock", "bond", "mutual_fund", "etf", "crypto"]
    symbols    = ["AAPL", "TSLA", "GOOGL", "AMZN", "BTC", "ETH", "NIFTY50", "SPY", "BOND10Y", "GOLD"]
    statuses   = ["active", "closed", "frozen"]

    def rdate(start="2020-01-01", end="2024-12-31"):
        s = date.fromisoformat(start)
        e = date.fromisoformat(end)
        return str(s + timedelta(days=random.randint(0, (e - s).days)))

    # Customers
    names = [
        "Arjun Sharma","Priya Patel","Rahul Gupta","Sneha Iyer","Vikram Mehta",
        "Alice Johnson","Bob Williams","Carol Davis","David Martinez","Eva Brown",
        "Liam Smith","Olivia Jones","Noah Wilson","Emma Taylor","Luca Rossi",
        "Sophie Mueller","Hans Becker","Yuki Tanaka","Chen Wei","Fatima Al-Hassan",
        "Carlos Rivera","Ana Lima","James O'Brien","Laura Blanc","Omar Khalid",
        "Nina Petrov","Ali Hassan","Mei Ling","Ivan Petrov","Sara Johansson"
    ]
    customers = []
    for i, name in enumerate(names, 1):
        email = name.lower().replace(" ", ".").replace("'", "") + f"@email.com"
        customers.append((i, name, email, random.choice(countries),
                          random.choice(segments), rdate("2018-01-01", "2022-12-31")))
    cur.executemany(
        "INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?,?)", customers)

    # Accounts (2-3 per customer)
    accounts = []
    acc_id = 1
    for cust_id in range(1, 31):
        for _ in range(random.randint(2, 3)):
            balance = round(random.uniform(500, 250000), 2)
            accounts.append((acc_id, cust_id, random.choice(acc_types),
                             balance, "USD", rdate("2018-01-01", "2023-01-01"),
                             random.choice(["active"] * 8 + ["closed", "frozen"])))
            acc_id += 1
    cur.executemany("INSERT OR IGNORE INTO accounts VALUES (?,?,?,?,?,?,?)", accounts)

    # Transactions (10-25 per account)
    txns = []
    txn_id = 1
    for acc in accounts:
        for _ in range(random.randint(10, 25)):
            ttype = random.choice(["credit", "debit"])
            amt   = round(random.uniform(10, 15000), 2)
            txns.append((txn_id, acc[0], ttype, amt,
                         random.choice(categories),
                         f"Txn {txn_id} desc",
                         rdate("2022-01-01", "2024-12-31")))
            txn_id += 1
    cur.executemany("INSERT OR IGNORE INTO transactions VALUES (?,?,?,?,?,?,?)", txns)

    # Loans
    loans = []
    for i in range(1, 51):
        cust_id = random.randint(1, 30)
        principal = round(random.uniform(5000, 500000), 2)
        rate = round(random.uniform(4.5, 18.5), 2)
        loans.append((i, cust_id, random.choice(loan_types), principal,
                      rate, random.choice([12, 24, 36, 60, 120, 240]),
                      rdate("2020-01-01", "2023-12-31"),
                      random.choice(["active"] * 7 + ["closed", "defaulted", "closed"])))
    cur.executemany("INSERT OR IGNORE INTO loans VALUES (?,?,?,?,?,?,?,?)", loans)

    # Investments
    invs = []
    inv_id = 1
    investment_accounts = [a for a in accounts if a[2] == "investment"]
    for acc in investment_accounts:
        for _ in range(random.randint(1, 4)):
            sym = random.choice(symbols)
            qty = round(random.uniform(1, 200), 4)
            pp  = round(random.uniform(10, 3000), 2)
            cp  = round(pp * random.uniform(0.7, 1.8), 2)
            invs.append((inv_id, acc[0], random.choice(assets),
                         sym, qty, pp, cp, rdate("2021-01-01", "2024-01-01")))
            inv_id += 1
    cur.executemany("INSERT OR IGNORE INTO investments VALUES (?,?,?,?,?,?,?,?)", invs)

    # Branches
    branches_data = [
        (1, "Mumbai Main",   "Mumbai",    "India",     "Ravi Kumar"),
        (2, "Delhi Central", "Delhi",     "India",     "Anita Singh"),
        (3, "NYC Downtown",  "New York",  "USA",       "Mark Spencer"),
        (4, "London HQ",     "London",    "UK",        "James Hart"),
        (5, "Singapore Hub", "Singapore", "Singapore", "Lily Tan"),
    ]
    cur.executemany("INSERT OR IGNORE INTO branches VALUES (?,?,?,?,?)", branches_data)

    conn.commit()
    conn.close()
    print(f"✅  Database created → {DB_PATH}")
    print(f"    customers: {len(customers)}, accounts: {len(accounts)}, "
          f"transactions: {len(txns)}, loans: {len(loans)}, investments: {len(invs)}")


# ─────────────────────────────────────────────
# 2.  BUILD THE DATASET (40 NL→SQL pairs)
# ─────────────────────────────────────────────

QUESTIONS = [
    # ── EASY (single table, simple filters) ──────────────────────────────
    {
        "id": 1, "difficulty": "easy",
        "question": "List all customers from India.",
        "gold_sql": "SELECT * FROM customers WHERE country = 'India';"
    },
    {
        "id": 2, "difficulty": "easy",
        "question": "How many customers are there in total?",
        "gold_sql": "SELECT COUNT(*) AS total_customers FROM customers;"
    },
    {
        "id": 3, "difficulty": "easy",
        "question": "Show all active accounts.",
        "gold_sql": "SELECT * FROM accounts WHERE status = 'active';"
    },
    {
        "id": 4, "difficulty": "easy",
        "question": "List all savings accounts with balance greater than 10000.",
        "gold_sql": "SELECT * FROM accounts WHERE account_type = 'savings' AND balance > 10000;"
    },
    {
        "id": 5, "difficulty": "easy",
        "question": "Show all defaulted loans.",
        "gold_sql": "SELECT * FROM loans WHERE status = 'defaulted';"
    },
    {
        "id": 6, "difficulty": "easy",
        "question": "List all credit transactions.",
        "gold_sql": "SELECT * FROM transactions WHERE txn_type = 'credit';"
    },
    {
        "id": 7, "difficulty": "easy",
        "question": "Show all premium segment customers.",
        "gold_sql": "SELECT * FROM customers WHERE segment = 'premium';"
    },
    {
        "id": 8, "difficulty": "easy",
        "question": "What is the highest account balance?",
        "gold_sql": "SELECT MAX(balance) AS max_balance FROM accounts;"
    },
    {
        "id": 9, "difficulty": "easy",
        "question": "List all stocks in the investments table.",
        "gold_sql": "SELECT * FROM investments WHERE asset_type = 'stock';"
    },
    {
        "id": 10, "difficulty": "easy",
        "question": "Show all mortgage loans.",
        "gold_sql": "SELECT * FROM loans WHERE loan_type = 'mortgage';"
    },

    # ── MEDIUM (aggregations, GROUP BY, single JOIN) ──────────────────────
    {
        "id": 11, "difficulty": "medium",
        "question": "What is the total balance across all active accounts?",
        "gold_sql": "SELECT SUM(balance) AS total_balance FROM accounts WHERE status = 'active';"
    },
    {
        "id": 12, "difficulty": "medium",
        "question": "How many accounts does each customer have? Show customer_id and account count.",
        "gold_sql": "SELECT customer_id, COUNT(*) AS account_count FROM accounts GROUP BY customer_id;"
    },
    {
        "id": 13, "difficulty": "medium",
        "question": "What is the average loan interest rate by loan type?",
        "gold_sql": "SELECT loan_type, AVG(interest_rate) AS avg_rate FROM loans GROUP BY loan_type;"
    },
    {
        "id": 14, "difficulty": "medium",
        "question": "Show the total transaction amount per category.",
        "gold_sql": "SELECT category, SUM(amount) AS total_amount FROM transactions GROUP BY category ORDER BY total_amount DESC;"
    },
    {
        "id": 15, "difficulty": "medium",
        "question": "List customers along with their total loan amount.",
        "gold_sql": "SELECT c.name, SUM(l.principal) AS total_loans FROM customers c JOIN loans l ON c.customer_id = l.customer_id GROUP BY c.customer_id, c.name;"
    },
    {
        "id": 16, "difficulty": "medium",
        "question": "Which accounts have more than 20 transactions?",
        "gold_sql": "SELECT account_id, COUNT(*) AS txn_count FROM transactions GROUP BY account_id HAVING COUNT(*) > 20;"
    },
    {
        "id": 17, "difficulty": "medium",
        "question": "What is the total debit amount per account?",
        "gold_sql": "SELECT account_id, SUM(amount) AS total_debit FROM transactions WHERE txn_type = 'debit' GROUP BY account_id;"
    },
    {
        "id": 18, "difficulty": "medium",
        "question": "Show the number of customers by country.",
        "gold_sql": "SELECT country, COUNT(*) AS customer_count FROM customers GROUP BY country ORDER BY customer_count DESC;"
    },
    {
        "id": 19, "difficulty": "medium",
        "question": "Find investments where current price is higher than purchase price (profitable investments).",
        "gold_sql": "SELECT * FROM investments WHERE current_price > purchase_price;"
    },
    {
        "id": 20, "difficulty": "medium",
        "question": "Show total principal of active loans grouped by loan type.",
        "gold_sql": "SELECT loan_type, SUM(principal) AS total_principal FROM loans WHERE status = 'active' GROUP BY loan_type;"
    },
    {
        "id": 21, "difficulty": "medium",
        "question": "List the top 5 accounts by balance.",
        "gold_sql": "SELECT account_id, customer_id, balance FROM accounts ORDER BY balance DESC LIMIT 5;"
    },
    {
        "id": 22, "difficulty": "medium",
        "question": "What is the average balance of savings accounts vs checking accounts?",
        "gold_sql": "SELECT account_type, AVG(balance) AS avg_balance FROM accounts WHERE account_type IN ('savings','checking') GROUP BY account_type;"
    },
    {
        "id": 23, "difficulty": "medium",
        "question": "Show customers who have at least one defaulted loan.",
        "gold_sql": "SELECT DISTINCT c.customer_id, c.name FROM customers c JOIN loans l ON c.customer_id = l.customer_id WHERE l.status = 'defaulted';"
    },
    {
        "id": 24, "difficulty": "medium",
        "question": "What is the total profit or loss from investments? (current_price - purchase_price) * quantity.",
        "gold_sql": "SELECT SUM((current_price - purchase_price) * quantity) AS total_pnl FROM investments;"
    },

    # ── HARD (multi-table JOINs, subqueries, window functions) ───────────
    {
        "id": 25, "difficulty": "hard",
        "question": "Show each customer's name, total account balance, and number of accounts.",
        "gold_sql": """SELECT c.name, COUNT(a.account_id) AS num_accounts, SUM(a.balance) AS total_balance
FROM customers c
JOIN accounts a ON c.customer_id = a.customer_id
GROUP BY c.customer_id, c.name
ORDER BY total_balance DESC;"""
    },
    {
        "id": 26, "difficulty": "hard",
        "question": "Find customers whose total debit transactions exceed 50000.",
        "gold_sql": """SELECT c.name, SUM(t.amount) AS total_debit
FROM customers c
JOIN accounts a ON c.customer_id = a.customer_id
JOIN transactions t ON a.account_id = t.account_id
WHERE t.txn_type = 'debit'
GROUP BY c.customer_id, c.name
HAVING SUM(t.amount) > 50000
ORDER BY total_debit DESC;"""
    },
    {
        "id": 27, "difficulty": "hard",
        "question": "List customers who have both a savings account and an investment account.",
        "gold_sql": """SELECT c.customer_id, c.name
FROM customers c
WHERE c.customer_id IN (SELECT customer_id FROM accounts WHERE account_type = 'savings')
  AND c.customer_id IN (SELECT customer_id FROM accounts WHERE account_type = 'investment');"""
    },
    {
        "id": 28, "difficulty": "hard",
        "question": "Show the monthly total transaction amount for 2024.",
        "gold_sql": """SELECT strftime('%Y-%m', txn_date) AS month, SUM(amount) AS total_amount
FROM transactions
WHERE txn_date LIKE '2024%'
GROUP BY month
ORDER BY month;"""
    },
    {
        "id": 29, "difficulty": "hard",
        "question": "Find the customer with the highest total investment portfolio value (current_price * quantity).",
        "gold_sql": """SELECT c.name, SUM(i.current_price * i.quantity) AS portfolio_value
FROM customers c
JOIN accounts a ON c.customer_id = a.customer_id
JOIN investments i ON a.account_id = i.account_id
GROUP BY c.customer_id, c.name
ORDER BY portfolio_value DESC
LIMIT 1;"""
    },
    {
        "id": 30, "difficulty": "hard",
        "question": "Show accounts that have no transactions.",
        "gold_sql": """SELECT a.account_id, a.customer_id, a.account_type, a.balance
FROM accounts a
LEFT JOIN transactions t ON a.account_id = t.account_id
WHERE t.txn_id IS NULL;"""
    },
    {
        "id": 31, "difficulty": "hard",
        "question": "Calculate the EMI for each active loan. EMI = principal * rate/1200 / (1 - (1 + rate/1200)^(-tenure)).",
        "gold_sql": """SELECT loan_id, customer_id, loan_type, principal, interest_rate, tenure_months,
    ROUND(principal * (interest_rate/1200) / (1 - POWER(1 + interest_rate/1200, -tenure_months)), 2) AS emi
FROM loans
WHERE status = 'active';"""
    },
    {
        "id": 32, "difficulty": "hard",
        "question": "Rank customers by their total balance across all accounts.",
        "gold_sql": """SELECT c.name, SUM(a.balance) AS total_balance,
    RANK() OVER (ORDER BY SUM(a.balance) DESC) AS balance_rank
FROM customers c
JOIN accounts a ON c.customer_id = a.customer_id
GROUP BY c.customer_id, c.name;"""
    },
    {
        "id": 33, "difficulty": "hard",
        "question": "Show the percentage of total transactions each category represents.",
        "gold_sql": """SELECT category,
    SUM(amount) AS category_total,
    ROUND(SUM(amount) * 100.0 / (SELECT SUM(amount) FROM transactions), 2) AS pct
FROM transactions
GROUP BY category
ORDER BY pct DESC;"""
    },
    {
        "id": 34, "difficulty": "hard",
        "question": "Find premium customers from India who have active loans above 100000.",
        "gold_sql": """SELECT DISTINCT c.name, c.email, l.loan_type, l.principal
FROM customers c
JOIN loans l ON c.customer_id = l.customer_id
WHERE c.segment = 'premium'
  AND c.country = 'India'
  AND l.status = 'active'
  AND l.principal > 100000;"""
    },
    {
        "id": 35, "difficulty": "hard",
        "question": "For each account, show the running total of transaction amounts ordered by date.",
        "gold_sql": """SELECT account_id, txn_date, amount,
    SUM(amount) OVER (PARTITION BY account_id ORDER BY txn_date) AS running_total
FROM transactions
ORDER BY account_id, txn_date;"""
    },
    {
        "id": 36, "difficulty": "hard",
        "question": "Show customers who have more loans than the average number of loans per customer.",
        "gold_sql": """SELECT c.name, COUNT(l.loan_id) AS loan_count
FROM customers c
JOIN loans l ON c.customer_id = l.customer_id
GROUP BY c.customer_id, c.name
HAVING COUNT(l.loan_id) > (
    SELECT AVG(cnt) FROM (
        SELECT COUNT(*) AS cnt FROM loans GROUP BY customer_id
    )
);"""
    },
    {
        "id": 37, "difficulty": "hard",
        "question": "Find accounts where total credits exceed total debits.",
        "gold_sql": """SELECT account_id,
    SUM(CASE WHEN txn_type='credit' THEN amount ELSE 0 END) AS total_credit,
    SUM(CASE WHEN txn_type='debit'  THEN amount ELSE 0 END) AS total_debit
FROM transactions
GROUP BY account_id
HAVING SUM(CASE WHEN txn_type='credit' THEN amount ELSE 0 END) >
       SUM(CASE WHEN txn_type='debit'  THEN amount ELSE 0 END);"""
    },
    {
        "id": 38, "difficulty": "hard",
        "question": "Show the most recent transaction for each account.",
        "gold_sql": """SELECT t.account_id, t.txn_id, t.amount, t.txn_type, t.txn_date
FROM transactions t
WHERE t.txn_date = (
    SELECT MAX(t2.txn_date) FROM transactions t2 WHERE t2.account_id = t.account_id
);"""
    },
    {
        "id": 39, "difficulty": "hard",
        "question": "Show total interest payable for each active loan. Total interest = EMI * tenure - principal.",
        "gold_sql": """SELECT loan_id, loan_type, principal, interest_rate, tenure_months,
    ROUND(
        ROUND(principal * (interest_rate/1200) / (1 - POWER(1 + interest_rate/1200, -tenure_months)), 2)
        * tenure_months - principal, 2
    ) AS total_interest
FROM loans
WHERE status = 'active';"""
    },
    {
        "id": 40, "difficulty": "hard",
        "question": "List the top 3 customers by total portfolio PnL (profit and loss from investments).",
        "gold_sql": """SELECT c.name,
    ROUND(SUM((i.current_price - i.purchase_price) * i.quantity), 2) AS total_pnl
FROM customers c
JOIN accounts a ON c.customer_id = a.customer_id
JOIN investments i ON a.account_id = i.account_id
GROUP BY c.customer_id, c.name
ORDER BY total_pnl DESC
LIMIT 3;"""
    },
]


def build_dataset():
    with open(DATASET_PATH, "w") as f:
        json.dump(QUESTIONS, f, indent=2)
    easy   = sum(1 for q in QUESTIONS if q["difficulty"] == "easy")
    medium = sum(1 for q in QUESTIONS if q["difficulty"] == "medium")
    hard   = sum(1 for q in QUESTIONS if q["difficulty"] == "hard")
    print(f"✅  Dataset saved → {DATASET_PATH}")
    print(f"    easy: {easy}  medium: {medium}  hard: {hard}  total: {len(QUESTIONS)}")


# ─────────────────────────────────────────────
if __name__ == "__main__":
    build_database()
    build_dataset()
    print("\n✅  Setup complete! Run 02_inference.py next.")