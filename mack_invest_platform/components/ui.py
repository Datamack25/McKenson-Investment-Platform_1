"""
Shared UI components used across pages.
"""
import streamlit as st
import streamlit.components.v1 as components


# ── CSS Theme ─────────────────────────────────────────────────────────────────

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

/* Scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg-secondary); }
::-webkit-scrollbar-thumb { background: var(--accent); border-radius: 3px; }

/* Headers */
h1, h2, h3 { font-family: 'Rajdhani', sans-serif; letter-spacing: 0.05em; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border);
}

/* Metric cards */
div[data-testid="metric-container"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px !important;
    box-shadow: var(--glow);
}

/* Buttons */
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

/* Select boxes, inputs */
.stSelectbox > div > div, .stNumberInput > div > div > input, .stTextInput > div > div > input {
    background: var(--bg-card2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    font-family: 'Share Tech Mono', monospace !important;
}

/* Tabs */
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

/* DataFrames */
.stDataFrame { border: 1px solid var(--border) !important; border-radius: 8px; }

/* Cards */
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
.neutral { color: var(--yellow) !important; }

/* Ticker strip */
.ticker-strip-wrap {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border);
    border-top: 1px solid var(--border);
    overflow: hidden;
    padding: 6px 0;
    margin-bottom: 0;
    white-space: nowrap;
}
.ticker-strip {
    display: inline-block;
    animation: marquee 60s linear infinite;
}
.ticker-strip:hover { animation-play-state: paused; }
.ticker-item {
    display: inline-block;
    margin: 0 24px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.82rem;
    letter-spacing: 0.05em;
}
.tick-up { color: var(--green); }
.tick-down { color: var(--red); }
@keyframes marquee {
    0%   { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}

/* News strip */
.news-strip-wrap {
    background: #0a0a0a;
    border: 1px solid rgba(255,60,60,0.4);
    border-radius: 4px;
    overflow: hidden;
    padding: 5px 0;
    margin: 6px 0;
}
.news-strip {
    display: inline-block;
    animation: marquee 90s linear infinite;
}
.news-item {
    display: inline-block;
    margin: 0 40px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.78rem;
    color: #ff8c00;
}
.news-tag {
    color: #ff3b6b;
    font-weight: bold;
    margin-right: 6px;
}

/* Section title */
.section-title {
    font-family: 'Rajdhani', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--accent);
    border-left: 3px solid var(--accent);
    padding-left: 10px;
    margin: 16px 0 10px;
}

/* Badge */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.08em;
}
.badge-green { background: rgba(0,255,136,0.15); color: var(--green); border: 1px solid var(--green); }
.badge-red { background: rgba(255,59,107,0.15); color: var(--red); border: 1px solid var(--red); }
.badge-blue { background: rgba(0,212,255,0.15); color: var(--accent); border: 1px solid var(--accent); }

/* Override streamlit default white blocks */
div[data-testid="stVerticalBlock"] { gap: 0.5rem; }
.block-container { padding-top: 1rem !important; max-width: 1400px; }
</style>
"""


def inject_css():
    st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)


# ── Ticker strip ──────────────────────────────────────────────────────────────

def render_ticker_strip(strip_data: list[dict]):
    items_html = ""
    for d in strip_data:
        t = d["ticker"]
        p = d["price"]
        pct = d["pct"]
        cls = "tick-up" if pct >= 0 else "tick-down"
        arrow = "▲" if pct >= 0 else "▼"
        price_fmt = f"{p:,.2f}" if p == p else "—"
        items_html += (
            f'<span class="ticker-item">'
            f'<b>{t}</b> &nbsp;{price_fmt}&nbsp;'
            f'<span class="{cls}">{arrow} {abs(pct):.2f}%</span>'
            f'</span>'
        )
    # Duplicate for seamless loop
    double = items_html * 2
    html = f"""
    <div class="ticker-strip-wrap">
        <div class="ticker-strip">{double}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ── News banner ───────────────────────────────────────────────────────────────

def render_news_banner(events_df):
    if events_df is None or events_df.empty:
        return
    items_html = ""
    for _, row in events_df.iterrows():
        move = row.get("move", "")
        scope = row.get("scope", "")
        headline = row.get("headline", "")
        start = str(row.get("start_dt", ""))[:16]
        end = str(row.get("end_dt", ""))[:16]
        items_html += (
            f'<span class="news-item">'
            f'<span class="news-tag">⚡ ALERT</span>'
            f'{headline} &bull; scope: <b>{scope}</b> &bull; move: <b>{move}</b> &bull; {start} → {end}'
            f'</span>'
        )
    double = items_html * 2
    html = f"""
    <div class="news-strip-wrap">
        <b style="color:#ff3b6b;font-family:Rajdhani;padding:0 12px;letter-spacing:0.1em;">BREAKING NEWS &bull; MARKET ALERT</b>
        <div class="news-strip">{double}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ── Section title ─────────────────────────────────────────────────────────────

def section_title(title: str):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


# ── Metric card row ───────────────────────────────────────────────────────────

def metric_row(metrics: list[dict]):
    """metrics = [{"label": ..., "value": ..., "color": "positive|negative|neutral"}]"""
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
