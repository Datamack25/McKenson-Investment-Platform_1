"""
Shared UI components used across pages.
ESLSCA Stock Market Game — v2.1
"""
import streamlit as st
import streamlit.components.v1 as components


# ── CSS Theme ─────────────────────────────────────────────────────────────────

DARK_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@300;400;500;600;700&family=Exo+2:wght@200;300;400;600;700&display=swap');

:root {
    --bg-primary:   #03070e;
    --bg-secondary: #0b1120;
    --bg-card:      #0f1923;
    --bg-card2:     #162030;
    --accent:       #00d4ff;
    --accent2:      #7c3aed;
    --green:        #00ff88;
    --red:          #ff3b6b;
    --yellow:       #ffd700;
    --orange:       #ff8c00;
    --text-primary: #e2e8f0;
    --text-secondary: #7a93b0;
    --border:       rgba(0, 212, 255, 0.18);
    --border-red:   rgba(255, 59, 107, 0.35);
    --glow:         0 0 24px rgba(0, 212, 255, 0.25);
    --glow-red:     0 0 16px rgba(255, 59, 107, 0.3);
    --glow-green:   0 0 16px rgba(0, 255, 136, 0.3);
}

/* ─── Base ─── */
html, body, .stApp {
    background-color: var(--bg-primary) !important;
    font-family: 'Exo 2', sans-serif;
    color: var(--text-primary);
}

/* Subtle scanline overlay */
.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0,0,0,0.03) 2px,
        rgba(0,0,0,0.03) 4px
    );
    pointer-events: none;
    z-index: 9999;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--bg-secondary); }
::-webkit-scrollbar-thumb { background: var(--accent); border-radius: 2px; }

/* Headers */
h1, h2, h3 { font-family: 'Rajdhani', sans-serif; letter-spacing: 0.05em; }

/* ─── Sidebar ─── */
section[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] label {
    color: var(--text-secondary) !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
}

/* ─── Metric cards ─── */
div[data-testid="metric-container"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px !important;
    box-shadow: var(--glow);
}

/* ─── Buttons ─── */
.stButton > button {
    background: linear-gradient(135deg, rgba(0,212,255,0.15), rgba(124,58,237,0.15)) !important;
    color: var(--accent) !important;
    border: 1px solid var(--accent) !important;
    border-radius: 4px !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, rgba(0,212,255,0.3), rgba(124,58,237,0.3)) !important;
    box-shadow: var(--glow) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active {
    transform: translateY(0) !important;
}

/* ─── Inputs ─── */
.stSelectbox > div > div,
.stNumberInput > div > div > input,
.stTextInput > div > div > input {
    background: var(--bg-card2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    font-family: 'Share Tech Mono', monospace !important;
    border-radius: 4px !important;
}
.stSlider > div > div > div > div {
    background: var(--accent) !important;
}

/* ─── Tabs ─── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--bg-secondary) !important;
    border-bottom: 1px solid var(--border);
    gap: 0;
}
.stTabs [data-baseweb="tab"] {
    color: var(--text-secondary) !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    padding: 8px 20px !important;
}
.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
    background: rgba(0,212,255,0.05) !important;
}

/* ─── DataFrames ─── */
.stDataFrame {
    border: 1px solid var(--border) !important;
    border-radius: 8px;
    overflow: hidden;
}
.stDataFrame thead tr th {
    background: var(--bg-card2) !important;
    color: var(--accent) !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}

/* ─── Info / warning / error ─── */
div[data-testid="stAlert"] {
    border-radius: 6px !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.82rem !important;
}

/* ─── Custom components ─── */
.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px 12px;
    text-align: center;
    box-shadow: var(--glow);
    transition: border-color 0.2s, box-shadow 0.2s;
}
.metric-card:hover {
    border-color: var(--accent);
    box-shadow: 0 0 32px rgba(0,212,255,0.35);
}
.metric-value {
    font-family: 'Share Tech Mono', monospace;
    font-size: 1.4rem;
    color: var(--accent);
    font-weight: bold;
    line-height: 1.2;
}
.metric-label {
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.7rem;
    color: var(--text-secondary);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 6px;
}

/* Color helpers */
.positive { color: var(--green) !important; }
.negative { color: var(--red) !important; }
.neutral  { color: var(--yellow) !important; }

/* Section title */
.section-title {
    font-family: 'Rajdhani', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--accent);
    border-left: 3px solid var(--accent);
    padding-left: 10px;
    margin: 20px 0 10px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, var(--border), transparent);
    margin-left: 10px;
}

/* Badges */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.badge-green { background: rgba(0,255,136,0.1); color: var(--green); border: 1px solid rgba(0,255,136,0.4); }
.badge-red   { background: rgba(255,59,107,0.1); color: var(--red);   border: 1px solid rgba(255,59,107,0.4); }
.badge-blue  { background: rgba(0,212,255,0.1);  color: var(--accent); border: 1px solid rgba(0,212,255,0.4); }

/* ─── Ticker strip ─── */
.ticker-strip-wrap {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border);
    border-top: 1px solid var(--border);
    overflow: hidden;
    padding: 7px 0;
    margin-bottom: 0;
    white-space: nowrap;
    position: relative;
}
.ticker-strip-wrap::before,
.ticker-strip-wrap::after {
    content: '';
    position: absolute;
    top: 0; bottom: 0;
    width: 60px;
    z-index: 2;
}
.ticker-strip-wrap::before {
    left: 0;
    background: linear-gradient(90deg, var(--bg-secondary), transparent);
}
.ticker-strip-wrap::after {
    right: 0;
    background: linear-gradient(-90deg, var(--bg-secondary), transparent);
}
.ticker-strip {
    display: inline-block;
    animation: marquee 60s linear infinite;
}
.ticker-strip:hover { animation-play-state: paused; }
.ticker-item {
    display: inline-block;
    margin: 0 20px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.8rem;
    letter-spacing: 0.04em;
}
.ticker-sep {
    color: var(--border);
    margin: 0 8px;
}
.tick-up   { color: var(--green); }
.tick-down { color: var(--red); }
@keyframes marquee {
    0%   { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}

/* ─── News banner ─── */
.news-strip-wrap {
    background: rgba(255,59,107,0.04);
    border: 1px solid var(--border-red);
    border-radius: 4px;
    overflow: hidden;
    padding: 5px 0;
    margin: 6px 0 4px;
    display: flex;
    align-items: center;
}
.news-label {
    flex-shrink: 0;
    padding: 0 14px;
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: var(--red);
    border-right: 1px solid var(--border-red);
    white-space: nowrap;
}
.news-scroll {
    overflow: hidden;
    flex: 1;
}
.news-strip {
    display: inline-block;
    animation: marquee 90s linear infinite;
    white-space: nowrap;
}
.news-item {
    display: inline-block;
    margin: 0 36px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.77rem;
    color: var(--orange);
}
.news-tag {
    color: var(--red);
    font-weight: bold;
    margin-right: 6px;
}

/* ─── Streamlit overrides ─── */
div[data-testid="stVerticalBlock"] { gap: 0.4rem; }
.block-container {
    padding-top: 0.8rem !important;
    padding-bottom: 1rem !important;
    max-width: 1440px;
}
</style>
"""


def inject_css():
    st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)


# ── Ticker strip ──────────────────────────────────────────────────────────────

def render_ticker_strip(strip_data: list[dict]):
    """Render a scrolling ticker strip. strip_data: list of {ticker, price, pct}."""
    if not strip_data:
        return

    items_html = ""
    for d in strip_data:
        t = d.get("ticker", "???")
        p = d.get("price", float("nan"))
        pct = d.get("pct", 0.0)

        cls = "tick-up" if pct >= 0 else "tick-down"
        arrow = "▲" if pct >= 0 else "▼"
        # Safe price formatting — handle NaN
        try:
            price_fmt = f"{float(p):,.2f}"
        except (ValueError, TypeError):
            price_fmt = "—"

        items_html += (
            f'<span class="ticker-item">'
            f'<b style="color:#e2e8f0;">{t}</b>'
            f'&nbsp;<span style="color:#94a3b8;">{price_fmt}</span>&nbsp;'
            f'<span class="{cls}">{arrow}&nbsp;{abs(pct):.2f}%</span>'
            f'</span>'
            f'<span class="ticker-sep">|</span>'
        )

    # Duplicate for seamless infinite loop
    double = items_html * 2
    html = (
        '<div class="ticker-strip-wrap">'
        f'<div class="ticker-strip">{double}</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ── News banner ───────────────────────────────────────────────────────────────

def render_news_banner(events_df):
    """Render a scrolling news/alert banner from an events DataFrame."""
    if events_df is None or events_df.empty:
        return

    items_html = ""
    for _, row in events_df.iterrows():
        move   = row.get("move", "")
        scope  = row.get("scope", "")
        headline = str(row.get("headline", "")).strip()
        start  = str(row.get("start_dt", ""))[:16]
        end    = str(row.get("end_dt",   ""))[:16]

        items_html += (
            f'<span class="news-item">'
            f'<span class="news-tag">⚡ ALERT</span>'
            f'{headline}'
            f'&nbsp;&bull;&nbsp;scope: <b>{scope}</b>'
            f'&nbsp;&bull;&nbsp;move: <b>{move}</b>'
            f'&nbsp;&bull;&nbsp;{start} → {end}'
            f'</span>'
        )

    if not items_html:
        return

    double = items_html * 2
    html = (
        '<div class="news-strip-wrap">'
        '<div class="news-label">⚡ BREAKING</div>'
        '<div class="news-scroll">'
        f'<div class="news-strip">{double}</div>'
        '</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ── Section title ─────────────────────────────────────────────────────────────

def section_title(title: str, icon: str = ""):
    prefix = f"{icon} " if icon else ""
    st.markdown(
        f'<div class="section-title">{prefix}{title}</div>',
        unsafe_allow_html=True,
    )


# ── Metric card row ───────────────────────────────────────────────────────────

def metric_row(metrics: list[dict]):
    """
    Render a horizontal row of metric cards.

    Each metric dict: {label: str, value: str, color: "positive"|"negative"|"neutral"|""}
    """
    if not metrics:
        return
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        cls   = m.get("color", "")
        label = m.get("label", "")
        value = m.get("value", "—")
        with col:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-label">{label}</div>'
                f'<div class="metric-value {cls}">{value}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
