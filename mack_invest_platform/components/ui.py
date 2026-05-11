"""
Shared UI components used across pages.
"""
import streamlit as st
import streamlit.components.v1 as components


DARK_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@300;400;500;600;700&family=Exo+2:wght@200;300;400;600;700&display=swap');

:root {
    --bg-primary: #030712;
    --bg-secondary: #0d1117;
    --bg-card: #111827;
    --bg-card2: #1a2332;
    --accent: #00d4ff;
    --accent2: #7c3aed;
    --green: #00ff88;
    --red: #ff3b6b;
    --yellow: #ffd700;
    --orange: #ff8c00;
    --text-primary: #e2e8f0;
    --text-secondary: #94a3b8;
    --border: rgba(0, 212, 255, 0.15);
    --glow: 0 0 20px rgba(0, 212, 255, 0.3);
}

html, body, .stApp {
    background-color: var(--bg-primary) !important;
    font-family: 'Exo 2', sans-serif;
    color: var(--text-primary);
}

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg-secondary); }
::-webkit-scrollbar-thumb { background: var(--accent); border-radius: 3px; }

h1, h2, h3 { font-family: 'Rajdhani', sans-serif; letter-spacing: 0.05em; }

section[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border);
}

div[data-testid="metric-container"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px !important;
    box-shadow: var(--glow);
}

.stButton > button {
    background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    box-shadow: 0 0 25px rgba(0, 212, 255, 0.5) !important;
    transform: translateY(-1px) !important;
}

.stSelectbox > div > div,
.stNumberInput > div > div > input,
.stTextInput > div > div > input {
    background: var(--bg-card2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    font-family: 'Share Tech Mono', monospace !important;
}

.stTabs [data-baseweb="tab-list"] {
    background: var(--bg-secondary) !important;
    border-bottom: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    color: var(--text-secondary) !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 600;
    letter-spacing: 0.05em;
}
.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
}

.stDataFrame { border: 1px solid var(--border) !important; border-radius: 8px; }

.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    text-align: center;
    box-shadow: var(--glow);
}
.metric-value {
    font-family: 'Share Tech Mono', monospace;
    font-size: 1.5rem;
    color: var(--accent);
    font-weight: bold;
}
.metric-label {
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.75rem;
    color: var(--text-secondary);
    letter-spacing: 0.1em;
    text-transform: uppercase;
}
.positive { color: var(--green) !important; }
.negative { color: var(--red) !important; }
.neutral  { color: var(--yellow) !important; }

/* ── MAM TABLE ── */
.mam-table-wrap {
    overflow-x: auto;
    border-radius: 8px;
    border: 1px solid rgba(0,212,255,0.12);
    margin-bottom: 12px;
}
.mam-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.78rem;
    color: #cbd5e1;
    background: rgba(13,17,23,0.8);
}
.mam-table tr:hover { background: rgba(0,212,255,0.04); }

/* ── INDICES BANNER (top, très fin) ── */
.indices-banner-wrap {
    background: #050a12;
    border-bottom: 1px solid rgba(0,212,255,0.2);
    overflow: hidden;
    white-space: nowrap;
    height: 24px;
    line-height: 24px;
    padding: 0;
    margin: 0;
    /* Pousse le bandeau sous le header Streamlit (~50px) */
    margin-top: 0px;
}
.indices-strip {
    display: inline-block;
    white-space: nowrap;
    animation: mam-marquee 50s linear infinite;
}
.idx-item {
    display: inline-block;
    margin: 0 18px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.72rem;
    vertical-align: middle;
}
.idx-sep { color: #1e3a4a; margin: 0 4px; }

/* ── TICKER STRIP (prix portefeuille) ── */
.ticker-strip-wrap {
    background: var(--bg-secondary);
    border-bottom: 1px solid rgba(0,212,255,0.25);
    border-top: 1px solid rgba(0,212,255,0.1);
    overflow: hidden;
    white-space: nowrap;
    height: 26px;
    line-height: 26px;
    padding: 0;
    margin: 0;
}
.ticker-strip {
    display: inline-block;
    white-space: nowrap;
    animation: mam-marquee 60s linear infinite;
}
.ticker-strip:hover { animation-play-state: paused; }
.ticker-item {
    display: inline-block;
    margin: 0 18px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.76rem;
    letter-spacing: 0.03em;
    vertical-align: middle;
}
.tick-up   { color: var(--green); }
.tick-down { color: var(--red);   }

/* ── NEWS BANNER (alertes/news) ── */
.news-strip-wrap {
    background: #08030a;
    border-bottom: 1px solid rgba(255,60,60,0.35);
    border-top: 1px solid rgba(255,60,60,0.2);
    overflow: hidden;
    white-space: nowrap;
    height: 24px;
    line-height: 24px;
    padding: 0;
    margin: 0;
    display: flex;
    align-items: center;
}
.news-label {
    flex-shrink: 0;
    background: #ff3b6b;
    color: #fff;
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: 0.65rem;
    letter-spacing: 0.14em;
    padding: 0 9px;
    height: 24px;
    line-height: 24px;
    white-space: nowrap;
}
.news-scroll-area {
    overflow: hidden;
    flex: 1;
    white-space: nowrap;
    height: 24px;
}
.news-strip {
    display: inline-block;
    white-space: nowrap;
    animation: mam-marquee 90s linear infinite;
}
.news-item {
    display: inline-block;
    margin: 0 32px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.70rem;
    color: #ff8c00;
    vertical-align: middle;
}
.news-tag { color: #ff3b6b; font-weight: bold; margin-right: 4px; }

@keyframes mam-marquee {
    0%   { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}

/* Push page content below the 3 fixed banners (~74px total) */
.block-container {
    padding-top: 0.6rem !important;
    max-width: 1400px;
}

/* Section title */
.section-title {
    font-family: 'Rajdhani', sans-serif;
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--accent);
    border-left: 3px solid var(--accent);
    padding-left: 10px;
    margin: 16px 0 10px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.badge { display:inline-block;padding:2px 8px;border-radius:12px;font-family:'Rajdhani',sans-serif;font-size:.75rem;font-weight:700;letter-spacing:.08em; }
.badge-green { background:rgba(0,255,136,.15);color:var(--green);border:1px solid var(--green); }
.badge-red   { background:rgba(255,59,107,.15);color:var(--red);  border:1px solid var(--red);  }
.badge-blue  { background:rgba(0,212,255,.15); color:var(--accent);border:1px solid var(--accent); }

div[data-testid="stVerticalBlock"] { gap: 0.4rem; }
</style>
"""


def inject_css():
    st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)


# ── Indices banner (très fin, tout en haut) ───────────────────────────────────
def render_indices_banner(indices_data: list[dict]):
    """indices_data = [{'label':..,'price':..,'pct':..}]"""
    if not indices_data:
        return
    items = ""
    for d in indices_data:
        pct = d.get("pct", 0)
        cls = "tick-up" if pct >= 0 else "tick-down"
        arrow = "▲" if pct >= 0 else "▼"
        p = d.get("price", 0)
        price_str = f"{p:,.2f}" if p and p == p else "—"
        items += (
            f'<span class="idx-item">'
            f'<b style="color:#7a93b0;">{d["label"]}</b> '
            f'<span style="color:#cbd5e1;">{price_str}</span> '
            f'<span class="{cls}">{arrow}{abs(pct):.2f}%</span>'
            f'</span>'
            f'<span class="idx-sep">|</span>'
        )
    double = items * 2
    st.markdown(
        f'<div class="indices-banner-wrap">'
        f'<div class="indices-strip">{double}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Ticker strip ──────────────────────────────────────────────────────────────
def render_ticker_strip(strip_data: list[dict]):
    if not strip_data:
        return
    items = ""
    for d in strip_data:
        t   = d.get("ticker", "")
        p   = d.get("price", float("nan"))
        pct = d.get("pct", 0)
        cls   = "tick-up" if pct >= 0 else "tick-down"
        arrow = "▲" if pct >= 0 else "▼"
        price_fmt = f"{p:,.2f}" if p == p else "—"
        items += (
            f'<span class="ticker-item">'
            f'<b style="color:#e2e8f0;">{t}</b> '
            f'<span style="color:#94a3b8;">{price_fmt}</span> '
            f'<span class="{cls}">{arrow}{abs(pct):.2f}%</span>'
            f'</span>'
            f'<span style="color:#1e3a4a;margin:0 3px;">│</span>'
        )
    double = items * 2
    st.markdown(
        f'<div class="ticker-strip-wrap">'
        f'<div class="ticker-strip">{double}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── News banner ───────────────────────────────────────────────────────────────
def render_news_banner(headlines):
    """
    Accept either:
      - a list of str  → each string is a headline
      - a DataFrame    → uses columns: headline, scope, move, start_dt, end_dt
    """
    import pandas as pd

    if headlines is None:
        return
    if isinstance(headlines, pd.DataFrame):
        if headlines.empty:
            return
        items = ""
        for _, row in headlines.iterrows():
            scope    = row.get("scope", "")
            headline = row.get("headline", "")
            move     = row.get("move", "")
            start    = str(row.get("start_dt", ""))[:16]
            end      = str(row.get("end_dt", ""))[:16]
            items += (
                f'<span class="news-item">'
                f'<span class="news-tag">⚡</span>'
                f'<b style="color:#ffd700;">{scope}</b> '
                f'{headline} '
                f'<span style="color:#7a93b0;">move:{move} {start}→{end}</span>'
                f'</span>'
                f'<span style="color:#4a0a0a;margin:0 6px;">◆</span>'
            )
    elif isinstance(headlines, list):
        if not headlines:
            return
        items = ""
        for h in headlines:
            items += (
                f'<span class="news-item">'
                f'<span class="news-tag">⚡</span>{h}'
                f'</span>'
                f'<span style="color:#4a0a0a;margin:0 6px;">◆</span>'
            )
    else:
        return

    double = items * 2
    st.markdown(
        f'<div class="news-strip-wrap">'
        f'<div class="news-label">📡 LIVE NEWS</div>'
        f'<div class="news-scroll-area">'
        f'<div class="news-strip">{double}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Section title ─────────────────────────────────────────────────────────────
def section_title(title: str, icon: str = ""):
    icon_html = f'<span style="font-size:1rem;">{icon}</span>' if icon else ""
    st.markdown(
        f'<div class="section-title">{icon_html}{title}</div>',
        unsafe_allow_html=True,
    )


# ── Metric card row ───────────────────────────────────────────────────────────
def metric_row(metrics: list[dict]):
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        cls = m.get("color", "")
        with col:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-label">{m["label"]}</div>'
                f'<div class="metric-value {cls}">{m["value"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── pnl_cell helper ───────────────────────────────────────────────────────────
def pnl_cell(value: float, suffix: str = "") -> str:
    col  = "#00ff88" if value >= 0 else "#ff3b6b"
    sign = "+" if value >= 0 else ""
    return f'<span style="color:{col};font-weight:bold;">{sign}{value:.2f}{suffix}</span>'
