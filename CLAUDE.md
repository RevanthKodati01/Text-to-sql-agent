# text-to-sql-agent

## Rules
- Python 3.10+, type hints everywhere, dataclasses for data objects.
- Keep prediction behind a single Predictor interface (question+schema -> SQL).
- The grader is the correctness contract: write it test-first, I review it myself.
- SQLite read-only connections only. No web frameworks, no auth, no ORM.
- Small focused modules. No file over ~120 lines.
- After each module, run it and show me output before continuing.
