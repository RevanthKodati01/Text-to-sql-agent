from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from texttosql.db import get_schema_from_db
from texttosql.grader import GradeResult, Grader
from texttosql.predictor import Predictor, PredictorInput


@dataclass
class EvalRow:
    question: str
    gold_sql: str
    db_path: str | None = None  # if set, overrides the default DB for this row


def load_pairs(path: Path) -> list[EvalRow]:
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            obj = json.loads(line)
            rows.append(EvalRow(
                question=obj["question"],
                gold_sql=obj["gold_sql"],
                db_path=obj.get("db_path"),
            ))
    return rows


def run_eval(
    pairs: list[EvalRow],
    predictor: Predictor,
    grader: Grader,
    schema: str,
    out_path: Path | None = None,
) -> list[GradeResult]:
    results: list[GradeResult] = []
    # TODO: resource leak — out handle not closed on exception; use try/finally
    out = open(out_path, "w") if out_path else None

    for i, row in enumerate(pairs, 1):
        # Per-row DB routing for multi-database benchmarks (e.g. BIRD)
        row_grader = Grader(row.db_path) if row.db_path else grader
        row_schema = get_schema_from_db(row.db_path) if row.db_path else schema

        inp = PredictorInput(question=row.question, schema=row_schema)
        pred_sql = predictor.predict(inp)
        result = row_grader.grade(row.question, row.gold_sql, pred_sql)
        results.append(result)

        mark = "PASS" if result.correct else "FAIL"
        print(f"[{i:02d}/{len(pairs):02d}] [{mark}] {row.question}")
        if not result.correct:
            print(f"         pred: {result.pred_sql}")
            if result.pred_error:
                print(f"        error: {result.pred_error}")
            else:
                print(f"    gold rows: {result.gold_rows}")
                print(f"    pred rows: {result.pred_rows}")

        if out:
            out.write(json.dumps(asdict(result)) + "\n")
            out.flush()

    if out:
        out.close()

    return results


def print_summary(results: list[GradeResult]) -> None:
    total = len(results)
    correct = sum(r.correct for r in results)
    pct = 100 * correct / total if total else 0
    print(f"\nAccuracy: {correct}/{total} ({pct:.1f}%)")
