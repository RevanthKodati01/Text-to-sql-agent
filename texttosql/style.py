CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"]  { font-family: 'Inter', sans-serif !important; }
#MainMenu, footer, header   { visibility: hidden; }
.block-container            { padding-top: 1rem !important; max-width: 1140px; }

/* ── Hero banner ─────────────────────────────────────────────── */
.hero {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 60%, #a855f7 100%);
    border-radius: 1rem;
    padding: 1.75rem 2.25rem;
    margin-bottom: 1.5rem;
    color: white;
}
.hero h1 { font-size: 1.7rem; font-weight: 700; margin: 0; letter-spacing: -0.02em; }
.hero p  { margin: 0.25rem 0 0; opacity: 0.82; font-size: 0.92rem; }

/* ── Cards ────────────────────────────────────────────────────── */
.card {
    background: #13131a;
    border: 1px solid #2d2d3f;
    border-radius: 0.75rem;
    padding: 1.1rem 1.25rem;
    margin-bottom: 0.75rem;
}
.card-label {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: #818cf8;
    margin-bottom: 0.6rem;
}

/* ── Grade banners ────────────────────────────────────────────── */
.grade-pass {
    background: linear-gradient(135deg, #064e3b, #065f46);
    border: 1px solid #10b981;
    border-radius: 0.75rem;
    padding: 0.9rem 1.5rem;
    color: #6ee7b7;
    font-weight: 600;
    font-size: 1rem;
    text-align: center;
    margin-top: 1.1rem;
}
.grade-fail {
    background: linear-gradient(135deg, #6b1a1a, #7f1d1d);
    border: 1px solid #ef4444;
    border-radius: 0.75rem;
    padding: 0.9rem 1.5rem;
    color: #fca5a5;
    font-weight: 600;
    font-size: 1rem;
    text-align: center;
    margin-top: 1.1rem;
}

/* ── Stat pills ───────────────────────────────────────────────── */
.pill-row  { display: flex; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 1rem; }
.pill      { background: #1e1e2e; border: 1px solid #2d2d3f; border-radius: 2rem;
             padding: 0.35rem 0.9rem; font-size: 0.8rem; color: #a78bfa; font-weight: 500; }
.pill b    { color: #e2e8f0; font-weight: 700; }
.pill-s    { color: #34d399; border-color: #34d39944; background: #064e3b22; }
.pill-m    { color: #fbbf24; border-color: #fbbf2444; background: #78350f22; }
.pill-c    { color: #f87171; border-color: #f8717144; background: #7f1d1d22; }

/* ── Primary button ───────────────────────────────────────────── */
div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
    border: none !important;
    border-radius: 0.5rem !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.75rem !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover { opacity: 0.88 !important; }

/* ── Inputs ───────────────────────────────────────────────────── */
.stTextInput input, .stTextArea textarea {
    background: #1e1e2e !important;
    border: 1px solid #2d2d3f !important;
    border-radius: 0.5rem !important;
    color: #e2e8f0 !important;
    font-size: 0.95rem !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {
    color: #64748b !important;
    opacity: 1 !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 2px #6366f133 !important;
}

/* ── Selectbox ────────────────────────────────────────────────── */
.stSelectbox [data-baseweb="select"] > div {
    background: #1e1e2e !important;
    border: 1px solid #2d2d3f !important;
    border-radius: 0.5rem !important;
    color: #e2e8f0 !important;
}

/* ── Sidebar ──────────────────────────────────────────────────── */
[data-testid="stSidebar"] { background: #0d0d14 !important; border-right: 1px solid #2d2d3f !important; }
[data-testid="stSidebar"] label { color: #94a3b8 !important; font-size: 0.8rem !important; font-weight: 500 !important; }
[data-testid="stSidebar"] .stSlider { padding-bottom: 0.5rem; }

/* ── Nav radio styled as tab pills ───────────────────────────── */
div[data-testid="stRadio"] > div[role="radiogroup"] {
    display: flex; flex-direction: row; gap: 0.4rem; background: transparent;
}
div[data-testid="stRadio"] label {
    background: #1e1e2e !important;
    border: 1px solid #2d2d3f !important;
    border-radius: 0.5rem !important;
    padding: 0.35rem 1.1rem !important;
    color: #94a3b8 !important;
    font-weight: 500 !important;
    cursor: pointer;
    transition: all 0.15s;
}
div[data-testid="stRadio"] label:has(input:checked) {
    background: #6366f1 !important;
    color: white !important;
    border-color: #6366f1 !important;
}
div[data-testid="stRadio"] label > div:first-child { display: none !important; }
div[data-testid="stRadio"] > label { display: none !important; }
</style>
"""
