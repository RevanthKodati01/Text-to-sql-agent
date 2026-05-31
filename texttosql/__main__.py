from __future__ import annotations

import argparse
import logging
from pathlib import Path

from texttosql.db import get_schema, seed
from texttosql.eval import load_pairs, print_summary, run_eval
from texttosql.grader import Grader
from texttosql.predictor import (
    LLMPredictor,
    MockPredictor,
    PredictorInput,
    RetryingPredictor,
)


def _build_predictor(args: argparse.Namespace, db: Path):
    if args.predictor == "mock":
        return MockPredictor()
    inner = LLMPredictor(model=args.model)
    if args.retries > 0:
        return RetryingPredictor(inner, db_path=db, max_retries=args.retries)
    return inner


def cmd_seed(args: argparse.Namespace) -> None:
    db = Path(args.db)
    db.parent.mkdir(parents=True, exist_ok=True)
    seed(db)
    print(f"Seeded {db}")


def cmd_eval(args: argparse.Namespace) -> None:
    db = Path(args.db)
    pairs = load_pairs(Path(args.pairs))
    if args.limit:
        pairs = pairs[: args.limit]
    predictor = _build_predictor(args, db)
    grader = Grader(db)
    out = Path(args.out) if args.out else None
    results = run_eval(pairs, predictor, grader, get_schema(), out_path=out)
    print_summary(results)


def cmd_query(args: argparse.Namespace) -> None:
    db = Path(args.db)
    predictor = _build_predictor(args, db)
    grader = Grader(db)

    inp = PredictorInput(question=args.question, schema=get_schema())
    pred_sql = predictor.predict(inp)
    print(f"Predicted SQL:\n  {pred_sql}\n")

    if args.gold:
        result = grader.grade(args.question, args.gold, pred_sql)
        mark = "PASS" if result.correct else "FAIL"
        print(f"Grade: {mark}")
        if not result.correct:
            print(f"  gold rows: {result.gold_rows}")
            print(f"  pred rows: {result.pred_rows}")
            if result.pred_error:
                print(f"  error    : {result.pred_error}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="texttosql")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    # seed
    p_seed = sub.add_parser("seed", help="Create and seed the demo database")
    p_seed.add_argument("--db", default="data/demo.db")

    # shared predictor flags
    def add_predictor_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--predictor", choices=["llm", "mock"], default="llm")
        p.add_argument("--model", default="gemini-2.5-flash")
        p.add_argument("--retries", type=int, default=2)

    # eval
    p_eval = sub.add_parser("eval", help="Run eval harness on a JSONL pairs file")
    p_eval.add_argument("--db", default="data/demo.db")
    p_eval.add_argument("--pairs", default="data/pairs.jsonl")
    p_eval.add_argument("--out", default=None, help="Write JSONL results to this file")
    p_eval.add_argument("--limit", type=int, default=None, help="Only run the first N pairs")
    add_predictor_args(p_eval)

    # query
    p_query = sub.add_parser("query", help="Grade a single question")
    p_query.add_argument("--db", default="data/demo.db")
    p_query.add_argument("--question", required=True)
    p_query.add_argument("--gold", default=None, help="Gold SQL to grade against")
    add_predictor_args(p_query)

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s  %(message)s",
    )

    {"seed": cmd_seed, "eval": cmd_eval, "query": cmd_query}[args.command](args)


if __name__ == "__main__":
    main()
