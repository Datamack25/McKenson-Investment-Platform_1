"""
Shared UI components used across pages.
"""
import streamlit as st

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

/* ═══════════════════════════════════════════════════
   TICKER STRIP — bandeau fin prix (28 px)
   ═══════════════════════════════════════════════════ */
.ticker-strip-wrap {
    width: 100%;
    height: 28px;
    line-height: 28px;
    overflow: hidden;
    white-space: nowrap;
    background: #0d1117;
    border-top: 1px solid rgba(0,212,255,0.25);
    border-bottom: 1px solid rgba(0,212,255,0.25);
    padding: 0;
    margin: 0;
    box-sizing: border-box;
}
.ticker-strip {
    display: inline-block;
    white-space: nowrap;
    animation: ticker-scroll 70s linear infinite;
    will-change: transform;
}
.ticker-strip:hover { animation-play-state: paused; }
.ticker-item {
    display: inline-block;
    padding: 0 18px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.03em;
    vertical-align: middle;
    line-height: 28px;
}
.ticker-sep {
    display: inline-block;
    color: #1e3a5f;
    vertical-align: middle;
    line-height: 28px;
    font-size: 0.7rem;
}
.tick-up   { color: #00ff88; }
.tick-down { color: #ff3b6b; }

/* ═══════════════════════════════════════════════════
   NEWS STRIP — bandeau fin alertes (26 px), juste en dessous
   ═══════════════════════════════════════════════════ */
.news-strip-wrap {
    width: 100%;
    height: 26px;
    overflow: hidden;
    white-space: nowrap;
    background: #080309;
    border-bottom: 1px solid rgba(255,59,107,0.35);
    display: flex;
    align-items: center;
    padding: 0;
    margin: 0;
    box-sizing: border-box;
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
    height: 26px;
    line-height: 26px;
    white-space: nowrap;
    text-transform: uppercase;
}
.news-scroll-area {
    flex: 1;
    overflow: hidden;
    white-space: nowrap;
    height: 26px;
    line-height: 26px;
}
.news-strip {
    display: inline-block;
    white-space: nowrap;
    animation: ticker-scroll 100s linear infinite;
    will-change: transform;
}
.news-item {
    display: inline-block;
    padding: 0 30px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.68rem;
    color: #ff8c00;
    vertical-align: middle;
    line-height: 26px;
}
.news-tag {
    color: #ff3b6b;
    font-weight: bold;
    margin-right: 4px;
}

/* Animation commune */
@keyframes ticker-scroll {
    0%   { transform: translateX(0); }
    100% { transform: translateX(-50%); }
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
.badge-red   { background: rgba(255,59,107,0.15); color: var(--red);   border: 1px solid var(--red);   }
.badge-blue  { background: rgba(0,212,255,0.15);  color: var(--accent); border: 1px solid var(--accent); }

div[data-testid="stVerticalBlock"] { gap: 0.5rem; }
.block-container { padding-top: 0.5rem !important; max-width: 1400px; }
</style>
"""


def inject_css():
    st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)


# ── Ticker strip (prix) ───────────────────────────────────────────────────────

def render_ticker_strip(strip_data: list):
    """Bandeau fin défilant — prix des actifs."""
    if not strip_data:
        return
    items_html = ""
    for d in strip_data:
        t   = d.get("ticker", "")
        p   = d.get("price", float("nan"))
        pct = d.get("pct", 0.0)
        cls   = "tick-up" if pct >= 0 else "tick-down"
        arrow = "▲" if pct >= 0 else "▼"
        price_fmt = f"{p:,.2f}" if p == p else "—"
        items_html += (
            f'<span class="ticker-item">'
            f'<b style="color:#cbd5e1;">{t}</b> '
            f'<span style="color:#e2e8f0;">{price_fmt}</span> '
            f'<span class="{cls}">{arrow}{abs(pct):.2f}%</span>'
            f'</span>'
            f'<span class="ticker-sep">|</span>'
        )
    # On double le contenu pour que le scroll soit continu sans blanc
    double = items_html * 2
    html = (
        '<div class="ticker-strip-wrap">'
        f'<div class="ticker-strip">{double}</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ── News banner (alertes) ─────────────────────────────────────────────────────

def render_news_banner(events_df):
    """Bandeau fin défilant — alertes de marché, placé juste sous le ticker."""
    if events_df is None or (hasattr(events_df, "empty") and events_df.empty):
        return
    items_html = ""
    for _, row in events_df.iterrows():
        move     = row.get("move", "")
        scope    = row.get("scope", "")
        headline = row.get("headline", "")
        start    = str(row.get("start_dt", ""))[:16]
        end      = str(row.get("end_dt",   ""))[:16]
        items_html += (
            f'<span class="news-item">'
            f'<span class="news-tag">⚡</span>'
            f'{headline}'
            f' &nbsp;·&nbsp; scope: <b style="color:#00d4ff;">{scope}</b>'
            f' &nbsp;·&nbsp; move: <b style="color:#ffd700;">{move}</b>'
            f' &nbsp;·&nbsp; {start} → {end}'
            f'</span>'
            f'<span style="color:#4a0010;padding:0 10px;">◆</span>'
        )
    if not items_html:
        return
    double = items_html * 2
    html = (
        '<div class="news-strip-wrap">'
        '<span class="news-label">⚡ BREAKING</span>'
        '<div class="news-scroll-area">'
        f'<div class="news-strip">{double}</div>'
        '</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ── Section title ─────────────────────────────────────────────────────────────

def section_title(title: str):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


# ── Metric card row ───────────────────────────────────────────────────────────

def metric_row(metrics: list):
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
