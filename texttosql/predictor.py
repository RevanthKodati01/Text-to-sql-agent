from __future__ import annotations

import logging
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from dotenv import load_dotenv
from google import genai
from google.genai.errors import ClientError

from texttosql.db import read_only

load_dotenv(Path(__file__).parent.parent / ".env")

log = logging.getLogger(__name__)

_PROMPT_TMPL = """\
You are a SQL expert. Given a SQLite schema and a natural-language question,
return a single valid SELECT statement and nothing else — no explanation,
no markdown fences, no trailing semicolon.

Schema:
{schema}

Question: {question}"""

_RETRY_TMPL = """\
You are a SQL expert. Your previous SQL attempt failed.

Schema:
{schema}

Question: {question}

Attempt {attempt} SQL:
{sql}

Problem: {problem}

Return only the corrected SELECT statement — no explanation, no markdown fences, no trailing semicolon."""


@dataclass
class PredictorInput:
    question: str
    schema: str


class Predictor(Protocol):
    def predict(self, inp: PredictorInput) -> str: ...


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip().rstrip(";")


def _parse_retry_delay(error_text: str, default: int = 30) -> int:
    """Extract seconds from 'Please retry in Xs' in a 429 message."""
    m = re.search(r"retry in (\d+)", error_text)
    return int(m.group(1)) if m else default


def _try_execute(db_path: str, sql: str) -> tuple[list[tuple], str | None]:
    """Run sql through the shared read_only() guard. Returns (rows, error_message)."""
    try:
        # TODO: resource leak — con.close() skipped on exception; use 'with' block
        con = read_only(db_path)
        rows = [tuple(r) for r in con.execute(sql).fetchall()]
        con.close()
        return rows, None
    except sqlite3.Error as exc:
        return [], str(exc)


class LLMPredictor:
    """Calls Gemini to produce SQL. One API call per predict()."""

    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        self._client = genai.Client()
        self._model = model

    def _call_api(self, prompt: str) -> str:
        """Call the API, sleeping and retrying once on 429."""
        for attempt in range(2):
            try:
                response = self._client.models.generate_content(
                    model=self._model, contents=prompt
                )
                if response.text is None:
                    finish = (
                        response.candidates[0].finish_reason
                        if response.candidates
                        else "unknown"
                    )
                    raise ValueError(f"Gemini returned no text (finish_reason={finish})")
                return _strip_fences(response.text)
            except ClientError as exc:
                if exc.code == 429 and attempt == 0:
                    wait = _parse_retry_delay(str(exc), default=30)
                    log.warning("Rate limited — waiting %ds", wait)
                    time.sleep(wait)
                else:
                    raise
        raise RuntimeError("unreachable")

    def predict(self, inp: PredictorInput) -> str:
        prompt = _PROMPT_TMPL.format(schema=inp.schema, question=inp.question)
        return self._call_api(prompt)

    def predict_with_feedback(
        self, inp: PredictorInput, prior_sql: str, problem: str, attempt: int
    ) -> str:
        prompt = _RETRY_TMPL.format(
            schema=inp.schema,
            question=inp.question,
            sql=prior_sql,
            problem=problem,
            attempt=attempt,
        )
        return self._call_api(prompt)


class RetryingPredictor:
    """Wraps any Predictor: retries up to max_retries times on SQL error or empty result."""

    def __init__(
        self,
        inner: LLMPredictor,
        db_path: Path | str,
        max_retries: int = 2,
    ) -> None:
        self._inner = inner
        self._db_path = str(db_path)
        self._max_retries = max_retries

    def predict(self, inp: PredictorInput) -> str:
        sql = self._inner.predict(inp)
        log.info("Attempt 1: %s", sql)

        for retry in range(1, self._max_retries + 1):
            rows, error = _try_execute(self._db_path, sql)

            if error is None and rows:
                log.info("Attempt %d succeeded (%d rows)", retry, len(rows))
                return sql

            problem = error if error else "query returned 0 rows"
            log.warning("Attempt %d failed — %s", retry, problem)

            sql = self._inner.predict_with_feedback(inp, sql, problem, retry)
            log.info("Attempt %d: %s", retry + 1, sql)

        # Validate the final generated SQL — the loop only checks before each retry.
        rows, error = _try_execute(self._db_path, sql)
        if error is None and rows:
            log.info("Attempt %d succeeded (%d rows)", self._max_retries + 1, len(rows))
        else:
            problem = error if error else "query returned 0 rows"
            log.warning("All %d attempts exhausted — last problem: %s", self._max_retries + 1, problem)
        return sql


class MockPredictor:
    """Returns a canned SQL string. Useful for harness tests."""

    def __init__(self, sql: str = "SELECT 1") -> None:
        self._sql = sql

    def predict(self, _inp: PredictorInput) -> str:
        return self._sql
