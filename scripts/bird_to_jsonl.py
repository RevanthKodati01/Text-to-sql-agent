"""
Convert a BIRD benchmark split into the JSONL format expected by this harness.

BIRD structure:
  dev/
    dev.json                          # list of question objects
    dev_databases/
      <db_id>/
        <db_id>.sqlite

Usage:
  python scripts/bird_to_jsonl.py \\
      --bird-json path/to/dev/dev.json \\
      --db-dir    path/to/dev/dev_databases \\
      --out       data/bird_dev.jsonl \\
      [--db-id    california_schools] \\
      [--difficulty simple|moderate|challenging] \\
      [--limit    50]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def convert(
    bird_json: Path,
    db_dir: Path,
    out: Path,
    db_id: str | None,
    difficulty: str | None,
    limit: int | None,
) -> None:
    entries: list[dict] = json.loads(bird_json.read_text())

    if db_id:
        entries = [e for e in entries if e["db_id"] == db_id]
    if difficulty:
        entries = [e for e in entries if e.get("difficulty") == difficulty]
    if limit:
        entries = entries[:limit]

    written = skipped = 0
    with out.open("w") as f:
        for entry in entries:
            db_path = db_dir / entry["db_id"] / f"{entry['db_id']}.sqlite"
            if not db_path.exists():
                print(f"  skip — DB not found: {db_path}")
                skipped += 1
                continue

            question = entry["question"]
            if entry.get("evidence", "").strip():
                question = f"{question}\nHint: {entry['evidence'].strip()}"

            row = {
                "question": question,
                "gold_sql": entry["SQL"],
                "db_path":  str(db_path.resolve()),
            }
            f.write(json.dumps(row) + "\n")
            written += 1

    print(f"Wrote {written} pairs to {out}" + (f" ({skipped} skipped)" if skipped else ""))


def main() -> None:
    p = argparse.ArgumentParser(description="Convert BIRD JSON to harness JSONL")
    p.add_argument("--bird-json",   required=True, type=Path)
    p.add_argument("--db-dir",      required=True, type=Path)
    p.add_argument("--out",         required=True, type=Path)
    p.add_argument("--db-id",       default=None, help="Filter to a single database")
    p.add_argument("--difficulty",  default=None, choices=["simple", "moderate", "challenging"])
    p.add_argument("--limit",       default=None, type=int)
    args = p.parse_args()

    if not args.bird_json.exists():
        raise SystemExit(f"Not found: {args.bird_json}")
    if not args.db_dir.exists():
        raise SystemExit(f"Not found: {args.db_dir}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    convert(args.bird_json, args.db_dir, args.out, args.db_id, args.difficulty, args.limit)


if __name__ == "__main__":
    main()
