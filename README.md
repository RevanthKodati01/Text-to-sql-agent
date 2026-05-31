# Text-to-SQL Agent

A text-to-SQL agent powered by Gemini with a full eval harness, retry loop, and Streamlit UI. Supports both a built-in demo database and the [BIRD benchmark](https://bird-bench.github.io/) (500 questions across 11 real-world databases).

---

## Features

- **Natural language → SQL** via Gemini (gemini-2.5-flash by default)
- **Retry loop** — on SQL error or empty result, feeds the error back to the model and retries (max 2×)
- **Grader** — executes both predicted and gold SQL, compares result sets as multisets (order-independent, float-tolerant)
- **BIRD benchmark** support — 500 questions, 11 databases, simple/moderate/challenging difficulty
- **Streamlit UI** — side-by-side predicted vs gold SQL, results tables, PASS/FAIL verdict, dataset browser
- **CLI** — `seed`, `eval`, `query` subcommands

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/your-username/text-to-sql-agent.git
cd text-to-sql-agent

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Add your Gemini API key

Get a free key at [aistudio.google.com](https://aistudio.google.com/apikey), then:

```bash
echo "GEMINI_API_KEY=your-key-here" > .env
```

### 3. Seed the demo database

```bash
python -m texttosql seed
```

### 4. Launch the UI

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## BIRD Benchmark Setup

The BIRD databases are not included in the repo (~3.3 GB). Download and convert them:

### 1. Download BIRD mini-dev

```bash
curl -L -o data/minidev.zip https://bird-bench.oss-cn-beijing.aliyuncs.com/minidev.zip
unzip data/minidev.zip -d data/bird_minidev
```

### 2. Convert to harness format

```bash
python scripts/bird_to_jsonl.py \
  --bird-json data/bird_minidev/minidev/MINIDEV/mini_dev_sqlite.json \
  --db-dir    data/bird_minidev/minidev/MINIDEV/dev_databases \
  --out       data/bird_dev.jsonl
```

Optional filters:

```bash
# Single database only
python scripts/bird_to_jsonl.py ... --db-id california_schools

# Simple questions only
python scripts/bird_to_jsonl.py ... --difficulty simple

# First 50 questions
python scripts/bird_to_jsonl.py ... --limit 50
```

### 3. Run the eval

```bash
# First 10 questions (saves API quota)
python -m texttosql eval --pairs data/bird_dev.jsonl --limit 10

# Full 500-question eval
python -m texttosql eval --pairs data/bird_dev.jsonl --out data/results.jsonl
```

---

## CLI Reference

```bash
# Seed the demo database
python -m texttosql seed [--db data/demo.db]

# Run eval harness
python -m texttosql eval [--pairs data/bird_dev.jsonl] [--limit N] [--out results.jsonl]
                         [--model gemini-2.5-flash] [--retries 2] [--predictor llm|mock]

# Grade a single question
python -m texttosql query --question "Which city has the most customers?" \
                          --gold "SELECT city FROM customers GROUP BY city ORDER BY COUNT(*) DESC LIMIT 1"

# Verbose mode (shows retry attempts)
python -m texttosql -v eval --pairs data/bird_dev.jsonl --limit 5
```

---

## Running Tests

```bash
pytest tests/ -v
```

13 grader contract tests — no API key or database download required.

---

## Project Structure

```
text-to-sql-agent/
├── app.py                   # Streamlit UI
├── requirements.txt
├── scripts/
│   └── bird_to_jsonl.py     # Converts BIRD JSON → harness JSONL
├── tests/
│   └── test_grader.py       # 13 grader contract tests
├── texttosql/
│   ├── __main__.py          # CLI (seed / eval / query)
│   ├── db.py                # Demo DB schema, seed, read-only connect
│   ├── eval.py              # Eval loop — loads pairs, grades, reports
│   ├── grader.py            # Executes SQL, compares result sets
│   ├── predictor.py         # LLMPredictor + RetryingPredictor
│   └── style.py             # Streamlit CSS
└── data/
    └── .gitkeep             # Databases and JSONL files go here (gitignored)
```

---

## How It Works

```
Question + Schema
      │
      ▼
 LLMPredictor  ──►  Gemini API  ──►  SQL
      │
      ▼
 RetryingPredictor
  • executes SQL read-only
  • if error or 0 rows → feeds error back to model → retry (max 2×)
      │
      ▼
   Grader
  • runs predicted SQL  ──►  result rows
  • runs gold SQL       ──►  result rows
  • compares as multisets (order-independent, float-tolerant)
  • returns GradeResult(correct, pred_rows, gold_rows, pred_error)
```

---

## Notes

- All SQLite connections are **read-only** (`?mode=ro` URI)
- The `Predictor` is a Python `Protocol` — swap in any backend (OpenAI, Ollama, mock) without changing the grader or eval loop
- Free Gemini API tier: ~20 requests/day on gemini-2.5-flash. Use `--limit` to stay within quota
