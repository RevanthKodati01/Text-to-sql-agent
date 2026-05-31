from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from texttosql.db import read_only


@dataclass
class GradeResult:
    correct: bool
    question: str
    gold_sql: str
    pred_sql: str
    gold_rows: list[tuple] = field(default_factory=list)
    pred_rows: list[tuple] = field(default_factory=list)
    pred_error: str | None = None


def _normalize(val: object) -> object:
    """Round floats to 9 dp to suppress floating-point arithmetic noise."""
    return round(val, 9) if isinstance(val, float) else val


def _counter(rows: list[tuple]) -> Counter:
    return Counter(tuple(_normalize(v) for v in row) for row in rows)


class Grader:
    def __init__(self, db_path: Path | str) -> None:
        self._db_path = str(db_path)

    def _connect(self) -> sqlite3.Connection:
        return read_only(self._db_path)

    def _fetch(self, con: sqlite3.Connection, sql: str) -> list[tuple]:
        cur = con.execute(sql)
        return [tuple(row) for row in cur.fetchall()]

    def grade(self, question: str, gold_sql: str, pred_sql: str) -> GradeResult:
        with self._connect() as con:
            gold_rows = self._fetch(con, gold_sql)
            try:
                pred_rows = self._fetch(con, pred_sql)
            except sqlite3.Error as exc:
                return GradeResult(
                    correct=False,
                    question=question,
                    gold_sql=gold_sql,
                    pred_sql=pred_sql,
                    gold_rows=gold_rows,
                    pred_rows=[],
                    pred_error=str(exc),
                )

        correct = _counter(gold_rows) == _counter(pred_rows)
        return GradeResult(
            correct=correct,
            question=question,
            gold_sql=gold_sql,
            pred_sql=pred_sql,
            gold_rows=gold_rows,
            pred_rows=pred_rows,
        )
