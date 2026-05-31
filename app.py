"""Streamlit UI for the text-to-SQL agent."""
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st

from texttosql.db import get_schema, get_schema_from_db, seed
from texttosql.eval import load_pairs
from texttosql.grader import Grader
from texttosql.predictor import LLMPredictor, PredictorInput, RetryingPredictor
from texttosql.style import CSS

DEMO_DB      = Path("data/demo.db")
BIRD_DB_DIR  = Path("data/bird_minidev/minidev/MINIDEV/dev_databases")
BIRD_JSON    = Path("data/bird_minidev/minidev/MINIDEV/mini_dev_sqlite.json")
DATA_DIR     = Path("data")

# ── helpers ───────────────────────────────────────────────────────────────────

@st.cache_resource
def _llm(model: str) -> LLMPredictor:
    return LLMPredictor(model=model)


@st.cache_data
def _db_stats(db_str: str) -> dict:
    con = sqlite3.connect(f"file:{db_str}?mode=ro", uri=True)
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    rows = sum(con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables)
    con.close()
    return {"tables": len(tables), "rows": rows, "names": tables}


def _list_dbs() -> dict[str, Path]:
    dbs: dict[str, Path] = {}
    if DEMO_DB.exists():
        dbs["demo (built-in)"] = DEMO_DB
    if BIRD_DB_DIR.exists():
        for d in sorted(BIRD_DB_DIR.iterdir()):
            db = d / f"{d.name}.sqlite"
            if db.exists():
                dbs[d.name] = db
    return dbs


def _run_sql(db_path: Path, sql: str) -> tuple[pd.DataFrame | None, str | None]:
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        df = pd.DataFrame(cur.fetchall(), columns=cols)
        con.close()
        return df, None
    except sqlite3.Error as exc:
        return None, str(exc)


def _sql_card(db_path: Path, sql: str, label: str) -> None:
    st.markdown(
        f'<div class="card"><div class="card-label">{label}</div></div>',
        unsafe_allow_html=True,
    )
    st.code(sql, language="sql")
    df, err = _run_sql(db_path, sql)
    if err:
        st.error(f"SQL error: {err}")
    elif df is None or df.empty:
        st.warning("Query returned 0 rows.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


# ── page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="Text-to-SQL Agent", page_icon="🔮", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

if not DEMO_DB.exists():
    DEMO_DB.parent.mkdir(parents=True, exist_ok=True)
    seed(DEMO_DB)

# ── sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Settings")
    dbs = _list_dbs()
    if not dbs:
        st.error("No databases found. Run: python -m texttosql seed")
        st.stop()

    db_label = st.selectbox("Database", list(dbs.keys()))
    db_path  = dbs[db_label]
    model    = st.selectbox("Model", ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-pro"])
    retries  = st.slider("Max retries", 0, 3, 2)

    st.divider()
    st.markdown("### 📊 DB Stats")
    stats = _db_stats(str(db_path))
    c1, c2 = st.columns(2)
    c1.metric("Tables", stats["tables"])
    c2.metric("Rows", f"{stats['rows']:,}")
    with st.expander("View schema"):
        schema_ddl = get_schema() if "demo" in db_label else get_schema_from_db(db_path)
        st.code(schema_ddl, language="sql")

# ── hero ──────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
  <h1>🔮 Text-to-SQL Agent</h1>
  <p>Ask anything in plain English — get SQL and results instantly, powered by Gemini</p>
</div>
""", unsafe_allow_html=True)

tab_query, tab_dataset = st.tabs(["🔍  Query", "📋  Dataset"])

# ── Query tab ─────────────────────────────────────────────────────────────────

with tab_query:
    question = st.text_input(
        "question",
        value=st.session_state.pop("prefill_q", ""),
        placeholder="e.g.  Which city has the most customers?",
        label_visibility="collapsed",
    )

    with st.expander("🎯 Add gold SQL to compare & grade  (optional)"):
        gold_input = st.text_area(
            "gold",
            value=st.session_state.pop("prefill_gold", ""),
            height=95,
            placeholder="SELECT ...",
            label_visibility="collapsed",
        )

    if st.button("▶  Generate SQL", type="primary", disabled=not question.strip()):
        schema    = get_schema() if "demo" in db_label else get_schema_from_db(db_path)
        inner     = _llm(model)
        predictor = RetryingPredictor(inner, db_path, retries) if retries else inner

        try:
            with st.spinner("Calling Gemini…"):
                pred_sql = predictor.predict(PredictorInput(question=question, schema=schema))
        except Exception as exc:
            st.error(f"API error: {exc}")
            st.stop()

        gold = gold_input.strip()
        if gold:
            left, right = st.columns(2)
            with left:
                _sql_card(db_path, pred_sql, "🤖 Predicted")
            with right:
                _sql_card(db_path, gold, "✅ Gold")
            result = Grader(db_path).grade(question, gold, pred_sql)
            cls  = "grade-pass" if result.correct else "grade-fail"
            text = "✅ PASS — result sets match" if result.correct else "❌ FAIL — result sets differ"
            st.markdown(f'<div class="{cls}">{text}</div>', unsafe_allow_html=True)
        else:
            _sql_card(db_path, pred_sql, "🤖 Predicted SQL")

# ── Dataset tab ───────────────────────────────────────────────────────────────

with tab_dataset:
    jsonl_files = sorted(DATA_DIR.glob("*.jsonl"))
    if not jsonl_files:
        st.info("No .jsonl files in data/.  Run `python -m texttosql seed` first.")
        st.stop()

    chosen = st.selectbox("Dataset file", [f.name for f in jsonl_files])
    pairs  = load_pairs(DATA_DIR / chosen)

    # difficulty pills for BIRD
    if "bird" in chosen and BIRD_JSON.exists():
        src   = json.loads(BIRD_JSON.read_text())
        diffs = Counter(e["difficulty"] for e in src)
        st.markdown(f"""
        <div class="pill-row">
          <div class="pill">Total <b>{len(pairs)}</b></div>
          <div class="pill pill-s">Simple <b>{diffs.get('simple', 0)}</b></div>
          <div class="pill pill-m">Moderate <b>{diffs.get('moderate', 0)}</b></div>
          <div class="pill pill-c">Challenging <b>{diffs.get('challenging', 0)}</b></div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="pill-row"><div class="pill">Total <b>{len(pairs)}</b></div></div>',
                    unsafe_allow_html=True)

    df = pd.DataFrame([
        {
            "#": i + 1,
            "Question": r.question.split("\nHint:")[0][:110] + ("…" if len(r.question) > 110 else ""),
            "Database": Path(r.db_path).parent.name if r.db_path else "demo",
            "Gold SQL":  r.gold_sql[:90] + "…",
        }
        for i, r in enumerate(pairs)
    ])

    st.caption("Select a row to preview its SQL — then load it into the Query tab.")
    sel = st.dataframe(df, use_container_width=True, on_select="rerun",
                       selection_mode="single-row", hide_index=True)

    if sel.selection.rows:
        row = pairs[sel.selection.rows[0]]
        st.divider()
        qa, qb = st.columns([4, 1])
        with qa:
            st.markdown(f"**{row.question.split(chr(10))[0]}**")
            st.code(row.gold_sql, language="sql")
        with qb:
            st.markdown("<br><br>", unsafe_allow_html=True)
            if st.button("Load into Query →", type="primary"):
                st.session_state["prefill_q"]    = row.question.split("\nHint:")[0]
                st.session_state["prefill_gold"] = row.gold_sql
                st.rerun()
