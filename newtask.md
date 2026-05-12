Let me give you the complete step by step workflow — exactly what to do, when, and with which model.Now let me give you every single command in exact order.

---

## Step 0 — Do this ONCE (5 minutes)

Open terminal on your MacBook:

```bash
# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Install LiteLLM (the proxy that lets Claude Code talk to any model)
pip install litellm requests

# Make sure Ollama is running
ollama serve
```

Open a second terminal and keep it ready. You'll need **2 terminals open at all times** — one for the proxy, one for Claude Code.

---

## The task prompt — copy this EXACTLY every time

Save this somewhere. You paste this into every model, zero changes:

```
Build a complete personal finance tracker project with:

BACKEND (FastAPI + Python):
- POST   /transactions     add transaction: amount, category, type (income/expense), date, note
- GET    /transactions     list all, filter by ?type= and ?category=
- GET    /transactions/id  get one transaction
- PUT    /transactions/id  update transaction
- DELETE /transactions/id  delete transaction
- GET    /summary          return total_income, total_expense, net_balance
- SQLite database, CORS middleware, proper 404/422 error handling, Pydantic models

FRONTEND (React):
- Dashboard page: 3 cards showing total income, total expense, net balance
- Transactions table: shows all transactions, filterable by type
- Add Transaction form: fields for amount, category, type, date, note
- Delete button on each table row
- Connects to backend at http://localhost:8000
- Plain CSS only, no UI libraries like Bootstrap or Material UI

Create all files needed to run both. Include requirements.txt and package.json.
```

---

## Model by model — exact commands

### Model 1 — DeepSeek-Coder (do this first, it's the best)

```bash
# Terminal 1 — start proxy
litellm --model ollama/deepseek-coder --port 4000

# Terminal 2 — run Claude Code
export ANTHROPIC_BASE_URL=http://localhost:4000
export ANTHROPIC_API_KEY=dummy

mkdir ~/Desktop/eval-deepseek && cd ~/Desktop/eval-deepseek
claude
# → paste the task prompt → wait for it to finish → type /exit
```

### Model 2 — CodeLlama

```bash
# Terminal 1 — kill previous proxy (Ctrl+C), then:
litellm --model ollama/codellama --port 4000

# Terminal 2
mkdir ~/Desktop/eval-codellama && cd ~/Desktop/eval-codellama
claude
# → paste prompt → wait → /exit
```

### Model 3 — Mistral

```bash
# Terminal 1
litellm --model ollama/mistral --port 4000

# Terminal 2
mkdir ~/Desktop/eval-mistral && cd ~/Desktop/eval-mistral
claude
# → paste prompt → wait → /exit
```

### Model 4 — Phi-3

```bash
# Terminal 1
litellm --model ollama/phi3 --port 4000

# Terminal 2
mkdir ~/Desktop/eval-phi3 && cd ~/Desktop/eval-phi3
claude
# → paste prompt → wait → /exit
```

### Model 5 — Gemini (get free key first)

Go to `aistudio.google.com` → click "Get API Key" → copy it. Free, no credit card.

```bash
# Terminal 1
litellm --model gemini/gemini-1.5-flash --api_key YOUR_GEMINI_KEY_HERE --port 4000

# Terminal 2
mkdir ~/Desktop/eval-gemini && cd ~/Desktop/eval-gemini
claude
# → paste prompt → wait → /exit
```

---

## After all 5 are done — score everything

```bash
cd ~/Desktop

# Score each model one by one
python evaluate.py --model deepseek      --dir eval-deepseek      --live
python evaluate.py --model codellama     --dir eval-codellama     --live
python evaluate.py --model mistral       --dir eval-mistral       --live
python evaluate.py --model phi3          --dir eval-phi3          --live
python evaluate.py --model gemini        --dir eval-gemini        --live

# Final comparison table
python evaluate.py --report
```

---

## What to expect from each model

| Model | Speed on Mac | Expected quality | Weakness |
|---|---|---|---|
| DeepSeek-Coder | Medium (4-6 min) | Best local — clean code | Sometimes over-engineers |
| CodeLlama | Medium (4-6 min) | Good structure | May miss frontend details |
| Mistral | Fast (3-4 min) | Decent backend, weak frontend | CSS often missing |
| Phi-3 | Very fast (1-2 min) | Basic, often incomplete | Misses error handling |
| Gemini Flash | Very fast (cloud) | Best overall | Needs internet |

---

## If LiteLLM gives errors

```bash
# Check if Ollama has the model
ollama list

# If a model shows wrong name, check exact name and use it:
litellm --model ollama/deepseek-coder:6.7b --port 4000

# If port 4000 is busy
litellm --model ollama/mistral --port 4001
# then also change:
export ANTHROPIC_BASE_URL=http://localhost:4001
```

Start with DeepSeek-Coder right now — it'll give you the best output and set a good baseline to compare others against. Come back and share what it generates and I'll help you score it!