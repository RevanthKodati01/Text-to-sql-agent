"""
Grader contract tests — written before grader.py exists.
Each test documents one invariant the grader must uphold.
"""
import sqlite3
import tempfile
from pathlib import Path

import pytest

from texttosql.grader import GradeResult, Grader


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    """Tiny in-test DB: one table with known rows."""
    path = tmp_path / "test.db"
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE nums (val INTEGER, label TEXT);
        INSERT INTO nums VALUES (1, 'one');
        INSERT INTO nums VALUES (2, 'two');
        INSERT INTO nums VALUES (2, 'two');   -- duplicate row
        INSERT INTO nums VALUES (3, NULL);    -- NULL value
    """)
    con.commit()
    con.close()
    return path


@pytest.fixture()
def grader(db_path: Path) -> Grader:
    return Grader(db_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

Q = "dummy question"
GOLD = "SELECT val, label FROM nums ORDER BY val"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCorrect:
    def test_identical_query_is_correct(self, grader: Grader) -> None:
        result = grader.grade(Q, GOLD, GOLD)
        assert result.correct is True

    def test_row_order_does_not_matter(self, grader: Grader) -> None:
        pred = "SELECT val, label FROM nums ORDER BY val DESC"
        result = grader.grade(Q, GOLD, pred)
        assert result.correct is True

    def test_multiset_duplicates_must_match(self, grader: Grader) -> None:
        # Gold returns two (2, 'two') rows; pred returns only one → wrong
        pred = "SELECT DISTINCT val, label FROM nums ORDER BY val"
        result = grader.grade(Q, GOLD, pred)
        assert result.correct is False

    def test_extra_row_in_pred_is_wrong(self, grader: Grader) -> None:
        gold = "SELECT val, label FROM nums WHERE val = 1"
        pred = "SELECT val, label FROM nums WHERE val <= 2"
        result = grader.grade(Q, gold, pred)
        assert result.correct is False

    def test_missing_row_in_pred_is_wrong(self, grader: Grader) -> None:
        gold = "SELECT val, label FROM nums WHERE val <= 2"
        pred = "SELECT val, label FROM nums WHERE val = 1"
        result = grader.grade(Q, gold, pred)
        assert result.correct is False


class TestNulls:
    def test_null_matches_null(self, grader: Grader) -> None:
        gold = "SELECT label FROM nums WHERE val = 3"
        pred = "SELECT label FROM nums WHERE val = 3"
        result = grader.grade(Q, gold, pred)
        assert result.correct is True
        assert result.gold_rows == [(None,)]

    def test_null_does_not_match_non_null(self, grader: Grader) -> None:
        gold = "SELECT label FROM nums WHERE val = 3"   # NULL
        pred = "SELECT label FROM nums WHERE val = 1"   # 'one'
        result = grader.grade(Q, gold, pred)
        assert result.correct is False


class TestSQLErrors:
    def test_syntax_error_is_incorrect(self, grader: Grader) -> None:
        result = grader.grade(Q, GOLD, "THIS IS NOT SQL")
        assert result.correct is False
        assert result.pred_error is not None
        assert isinstance(result.pred_error, str)
        assert len(result.pred_error) > 0

    def test_unknown_table_is_incorrect(self, grader: Grader) -> None:
        result = grader.grade(Q, GOLD, "SELECT * FROM nonexistent_table")
        assert result.correct is False
        assert result.pred_error is not None

    def test_gold_rows_still_populated_on_pred_error(self, grader: Grader) -> None:
        result = grader.grade(Q, GOLD, "BAD SQL")
        assert len(result.gold_rows) > 0
        assert result.pred_rows == []


class TestGradeResultFields:
    def test_fields_are_echoed(self, grader: Grader) -> None:
        pred = "SELECT val, label FROM nums WHERE val = 1"
        result = grader.grade("my question", GOLD, pred)
        assert result.question == "my question"
        assert result.gold_sql == GOLD
        assert result.pred_sql == pred

    def test_rows_are_lists_of_tuples(self, grader: Grader) -> None:
        result = grader.grade(Q, GOLD, GOLD)
        assert isinstance(result.gold_rows, list)
        assert all(isinstance(r, tuple) for r in result.gold_rows)
        assert isinstance(result.pred_rows, list)
        assert all(isinstance(r, tuple) for r in result.pred_rows)

    def test_no_error_when_correct(self, grader: Grader) -> None:
        result = grader.grade(Q, GOLD, GOLD)
        assert result.pred_error is None
