# Text-to-SQL Agent — Spec

## Overview

A self-contained eval harness for natural-language-to-SQL prediction. Given a question
and a schema, a Predictor produces SQL. A Grader executes both the predicted and gold SQL
against a shared SQLite database and compares their result sets. A CLI drives the whole loop.

---

## 1. Predictor Interface

```
question: str
schema:   str          # DDL string, e.g. CREATE TABLE ... statements
─────────────────────
returns:  str          # a single SQL SELECT statement
```

**Contract**
- Input is a natural-language question and the full DDL for the relevant tables.
- Output is a single SQL string — no explanation, no markdown fences.
- The interface is a Python Protocol so any backend (LLM, heuristic, mock) can satisfy it.
- Implementations are stateless: no side effects, no mutation of the DB.

**Dataclass**

```python
@dataclass
class PredictorInput:
    question: str
    schema: str

# Predictor is a Protocol:
# def predict(self, inp: PredictorInput) -> str
```

---

## 2. Grader

The grader is the correctness contract. It is the only place that touches the database
at evaluation time.

**Algorithm**

1. Open a read-only SQLite connection to the demo DB.
2. Execute the gold SQL → collect rows as a multiset (Counter of tuples).
3. Execute the predicted SQL → collect rows as a multiset.
4. Compare: exact multiset equality = correct.
5. Return a `GradeResult` dataclass.

**GradeResult fields**

| field | type | meaning |
|---|---|---|
| `correct` | `bool` | multisets are equal |
| `gold_rows` | `list[tuple]` | rows from gold SQL |
| `pred_rows` | `list[tuple]` | rows from predicted SQL |
| `pred_error` | `str \| None` | SQL error if prediction failed to execute |
| `question` | `str` | echoed from input |
| `gold_sql` | `str` | echoed from input |
| `pred_sql` | `str` | echoed from input |

**Edge cases**
- Predicted SQL raises a sqlite3 exception → `correct=False`, `pred_error` populated.
- Column order in SELECT does not matter for correctness (rows are tuples, so column
  order *does* matter — gold SQL is authoritative for column ordering).
- Row order does not matter (multiset).
- NULL values are compared as-is (Python `None`).

**What the grader does NOT do**
- It does not parse or lint SQL.
- It does not normalise whitespace or aliases.
- It does not reward partial credit.

---

## 3. Demo SQLite Database

A minimal schema with enough variety to write interesting questions.

### Schema (3 tables)

```sql
CREATE TABLE customers (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL,
    city    TEXT NOT NULL,
    joined  DATE NOT NULL          -- 'YYYY-MM-DD'
);

CREATE TABLE products (
    id       INTEGER PRIMARY KEY,
    name     TEXT NOT NULL,
    category TEXT NOT NULL,
    price    REAL NOT NULL
);

CREATE TABLE orders (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL,
    ordered_at  DATE NOT NULL      -- 'YYYY-MM-DD'
);
```

### Seed Data (illustrative, not exhaustive)

- 5 customers across 3 cities.
- 8 products in 3 categories (electronics, books, clothing).
- ~15 orders spanning two calendar years.

Chosen to support questions involving: aggregation, GROUP BY, JOIN, WHERE with date
filtering, ORDER BY + LIMIT, subqueries, and HAVING.

### Example eval pairs

| question | gold SQL (sketch) |
|---|---|
| How many orders did each customer place? | SELECT name, COUNT(*) FROM customers JOIN orders … GROUP BY … |
| Which product has the highest total revenue? | SELECT name, SUM(price*quantity) … ORDER BY … LIMIT 1 |
| List customers who have never placed an order. | SELECT name FROM customers WHERE id NOT IN (SELECT customer_id FROM orders) |
| What is the average order value in 2024? | SELECT AVG(price*quantity) FROM orders JOIN products … WHERE ordered_at LIKE '2024%' |

---

## 4. CLI

Single entry point: `python -m texttosql`.

### Commands

#### `eval`
Run the full eval harness against a JSONL file of question/gold-SQL pairs.

```
python -m texttosql eval --db path/to/demo.db \
                         --pairs path/to/pairs.jsonl \
                         [--predictor mock|llm] \
                         [--out results.jsonl]
```

Output: per-row `GradeResult` written to stdout (or `--out` file) as JSONL,
followed by a summary line:

```
Accuracy: 7/10 (70.0%)
```

#### `query`
One-shot: ask a single question interactively and print the predicted SQL + grade.

```
python -m texttosql query --db path/to/demo.db \
                          --question "Which city has the most customers?" \
                          --gold "SELECT city, COUNT(*) …"
```

#### `seed`
Create and seed the demo database from scratch.

```
python -m texttosql seed --db path/to/demo.db
```

---

## 5. Module Layout (target)

```
text-to-sql-agent/
├── CLAUDE.md
├── spec.md
├── texttosql/
│   ├── __init__.py
│   ├── __main__.py       # CLI dispatcher           ≤60 lines
│   ├── predictor.py      # Protocol + MockPredictor ≤80 lines
│   ├── grader.py         # Grader + GradeResult     ≤100 lines
│   ├── db.py             # seed + read-only connect ≤80 lines
│   └── eval.py           # eval loop + reporting    ≤80 lines
├── data/
│   ├── demo.db           # generated by `seed`
│   └── pairs.jsonl       # eval pairs
└── tests/
    └── test_grader.py    # written before grader.py
```

---

## 6. Build Order

1. `tests/test_grader.py` — grader contract tests (no implementation yet).
2. `texttosql/db.py` — schema + seed.
3. `texttosql/grader.py` — until tests pass.
4. `texttosql/predictor.py` — Protocol + Mock.
5. `texttosql/eval.py` — eval loop.
6. `texttosql/__main__.py` — CLI wiring.
7. `data/pairs.jsonl` — eval pairs for the demo DB.
