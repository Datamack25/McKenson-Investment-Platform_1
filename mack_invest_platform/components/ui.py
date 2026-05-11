"""
components/ui.py  —  MAM v3.3
Bandeaux fins horizontaux :
  1. render_indices_banner  → indices boursiers (clés: symbol/name/emoji/price/pct)
  2. render_ticker_strip    → tickers portefeuille (clés: ticker/price/pct)
  3. render_news_banner     → headlines (list[dict] avec clé 'title'+'category', ou list[str])
"""
import streamlit as st

DARK_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@300;400;500;600;700&family=Exo+2:wght@200;300;400;600;700&display=swap');

:root {
    --bg-primary:#030712; --bg-secondary:#0d1117; --bg-card:#111827; --bg-card2:#1a2332;
    --accent:#00d4ff; --accent2:#7c3aed; --green:#00ff88; --red:#ff3b6b;
    --yellow:#ffd700; --orange:#ff8c00;
    --text-primary:#e2e8f0; --text-secondary:#94a3b8;
    --border:rgba(0,212,255,0.15); --glow:0 0 20px rgba(0,212,255,0.3);
}
html,body,.stApp { background-color:var(--bg-primary)!important; font-family:'Exo 2',sans-serif; color:var(--text-primary); }
::-webkit-scrollbar{width:5px;height:5px} ::-webkit-scrollbar-track{background:var(--bg-secondary)} ::-webkit-scrollbar-thumb{background:var(--accent);border-radius:3px}
h1,h2,h3{font-family:'Rajdhani',sans-serif;letter-spacing:.05em}
section[data-testid="stSidebar"]{background:var(--bg-secondary)!important;border-right:1px solid var(--border)}
div[data-testid="metric-container"]{background:var(--bg-card)!important;border:1px solid var(--border);border-radius:8px;padding:12px!important;box-shadow:var(--glow)}
.stButton>button{background:linear-gradient(135deg,var(--accent),var(--accent2))!important;color:#fff!important;border:none!important;border-radius:6px!important;font-family:'Rajdhani',sans-serif!important;font-weight:600!important;letter-spacing:.08em!important;transition:all .2s!important}
.stButton>button:hover{box-shadow:0 0 25px rgba(0,212,255,.5)!important;transform:translateY(-1px)!important}
.stSelectbox>div>div,.stNumberInput>div>div>input,.stTextInput>div>div>input{background:var(--bg-card2)!important;border:1px solid var(--border)!important;color:var(--text-primary)!important;font-family:'Share Tech Mono',monospace!important}
.stTabs [data-baseweb="tab-list"]{background:var(--bg-secondary)!important;border-bottom:1px solid var(--border)}
.stTabs [data-baseweb="tab"]{color:var(--text-secondary)!important;font-family:'Rajdhani',sans-serif!important;font-weight:600;letter-spacing:.05em}
.stTabs [aria-selected="true"]{color:var(--accent)!important;border-bottom:2px solid var(--accent)!important}
.stDataFrame{border:1px solid var(--border)!important;border-radius:8px}
.metric-card{background:var(--bg-card);border:1px solid var(--border);border-radius:10px;padding:16px;text-align:center;box-shadow:var(--glow)}
.metric-value{font-family:'Share Tech Mono',monospace;font-size:1.5rem;color:var(--accent);font-weight:bold}
.metric-label{font-family:'Rajdhani',sans-serif;font-size:.75rem;color:var(--text-secondary);letter-spacing:.1em;text-transform:uppercase}
.positive{color:var(--green)!important} .negative{color:var(--red)!important} .neutral{color:var(--yellow)!important}
.mam-table-wrap{overflow-x:auto;border-radius:8px;border:1px solid rgba(0,212,255,.12);margin-bottom:12px}
.mam-table{width:100%;border-collapse:collapse;font-family:'Share Tech Mono',monospace;font-size:.78rem;color:#cbd5e1;background:rgba(13,17,23,.8)}
.mam-table tr:hover{background:rgba(0,212,255,.04)}
.badge{display:inline-block;padding:2px 8px;border-radius:12px;font-family:'Rajdhani',sans-serif;font-size:.75rem;font-weight:700;letter-spacing:.08em}
.badge-green{background:rgba(0,255,136,.15);color:var(--green);border:1px solid var(--green)}
.badge-red{background:rgba(255,59,107,.15);color:var(--red);border:1px solid var(--red)}
.badge-blue{background:rgba(0,212,255,.15);color:var(--accent);border:1px solid var(--accent)}
.section-title{font-family:'Rajdhani',sans-serif;font-size:1.05rem;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:var(--accent);border-left:3px solid var(--accent);padding-left:10px;margin:16px 0 10px;display:flex;align-items:center;gap:8px}
div[data-testid="stVerticalBlock"]{gap:.4rem}
.block-container{padding-top:.5rem!important;max-width:1400px}

/* ══ BANDEAU 1 : INDICES (tout en haut, fond très sombre) ══ */
.idx-wrap{
    background:#020810;
    border-bottom:1px solid rgba(0,212,255,.18);
    overflow:hidden;
    white-space:nowrap;
    height:26px;
    line-height:26px;
    display:flex;
    align-items:center;
}
.idx-label{
    flex-shrink:0;
    background:rgba(0,212,255,.12);
    color:#00d4ff;
    font-family:'Rajdhani',sans-serif;
    font-weight:700;font-size:.62rem;letter-spacing:.16em;
    padding:0 10px;height:26px;line-height:26px;white-space:nowrap;
    border-right:1px solid rgba(0,212,255,.2);
}
.idx-scroll{overflow:hidden;flex:1;height:26px;white-space:nowrap}
.idx-strip{display:inline-block;white-space:nowrap;animation:mam-run 55s linear infinite}
.idx-item{display:inline-block;padding:0 16px;font-family:'Share Tech Mono',monospace;font-size:.72rem;vertical-align:middle}
.idx-sep{color:#0d2030;padding:0 4px}

/* ══ BANDEAU 2 : TICKER PORTEFEUILLE ══ */
.tkr-wrap{
    background:#030d15;
    border-bottom:1px solid rgba(0,212,255,.22);
    overflow:hidden;
    white-space:nowrap;
    height:24px;
    line-height:24px;
    display:flex;
    align-items:center;
}
.tkr-label{
    flex-shrink:0;
    background:rgba(0,212,255,.08);
    color:#7a93b0;
    font-family:'Rajdhani',sans-serif;
    font-weight:700;font-size:.58rem;letter-spacing:.16em;
    padding:0 9px;height:24px;line-height:24px;white-space:nowrap;
    border-right:1px solid rgba(0,212,255,.15);
}
.tkr-scroll{overflow:hidden;flex:1;height:24px;white-space:nowrap}
.tkr-strip{display:inline-block;white-space:nowrap;animation:mam-run 60s linear infinite}
.tkr-item{display:inline-block;padding:0 14px;font-family:'Share Tech Mono',monospace;font-size:.70rem;vertical-align:middle}

/* ══ BANDEAU 3 : NEWS ══ */
.news-wrap{
    background:#08030e;
    border-bottom:1px solid rgba(255,60,60,.28);
    overflow:hidden;
    white-space:nowrap;
    height:24px;
    line-height:24px;
    display:flex;
    align-items:center;
}
.news-label{
    flex-shrink:0;
    background:#ff3b6b;
    color:#fff;
    font-family:'Rajdhani',sans-serif;
    font-weight:700;font-size:.60rem;letter-spacing:.16em;
    padding:0 9px;height:24px;line-height:24px;white-space:nowrap;
}
.news-scroll{overflow:hidden;flex:1;height:24px;white-space:nowrap}
.news-strip{display:inline-block;white-space:nowrap;animation:mam-run 90s linear infinite}
.news-item{display:inline-block;padding:0 28px;font-family:'Share Tech Mono',monospace;font-size:.68rem;color:#ff8c00;vertical-align:middle}
.news-cat{color:#ff3b6b;font-weight:bold;margin-right:5px}

.tick-up{color:#00ff88} .tick-down{color:#ff3b6b}

@keyframes mam-run{
    0%  {transform:translateX(0)}
    100%{transform:translateX(-50%)}
}
</style>
"""


def inject_css():
    st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)


# ── Bandeau 1 : Indices boursiers ─────────────────────────────────────────────
def render_indices_banner(indices_data: list[dict]):
    """
    indices_data vient de get_indices_data() :
    [{"symbol":..,"name":..,"emoji":..,"price":..,"pct":..}]
    """
    if not indices_data:
        return
    items = ""
    for d in indices_data:
        label = d.get("name") or d.get("label") or d.get("ticker", "")
        emoji = d.get("emoji", "")
        pct   = d.get("pct", 0) or 0
        price = d.get("price", 0) or 0
        cls   = "tick-up" if pct >= 0 else "tick-down"
        arrow = "▲" if pct >= 0 else "▼"
        p_str = f"{price:,.2f}" if price and price == price else "—"
        items += (
            f'<span class="idx-item">'
            f'{emoji} <b style="color:#94a3b8;">{label}</b> '
            f'<span style="color:#cbd5e1;">{p_str}</span> '
            f'<span class="{cls}">{arrow}{abs(pct):.2f}%</span>'
            f'</span>'
            f'<span class="idx-sep">│</span>'
        )
    double = items * 2
    st.markdown(
        f'<div class="idx-wrap">'
        f'<div class="idx-label">📡 INDICES</div>'
        f'<div class="idx-scroll"><div class="idx-strip">{double}</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Bandeau 2 : Ticker portefeuille ──────────────────────────────────────────
def render_ticker_strip(strip_data: list[dict]):
    """
    strip_data vient de get_strip_data() :
    [{"ticker":..,"price":..,"pct":..}]
    """
    if not strip_data:
        return
    items = ""
    for d in strip_data:
        t     = d.get("ticker", "")
        price = d.get("price", 0) or 0
        pct   = d.get("pct", 0) or 0
        cls   = "tick-up" if pct >= 0 else "tick-down"
        arrow = "▲" if pct >= 0 else "▼"
        p_str = f"{price:,.2f}" if price and price == price else "—"
        items += (
            f'<span class="tkr-item">'
            f'<b style="color:#e2e8f0;">{t}</b> '
            f'<span style="color:#7a93b0;">{p_str}</span> '
            f'<span class="{cls}">{arrow}{abs(pct):.2f}%</span>'
            f'</span>'
            f'<span style="color:#0d2030;padding:0 3px;">·</span>'
        )
    double = items * 2
    st.markdown(
        f'<div class="tkr-wrap">'
        f'<div class="tkr-label">LIVE</div>'
        f'<div class="tkr-scroll"><div class="tkr-strip">{double}</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Bandeau 3 : News ─────────────────────────────────────────────────────────
def render_news_banner(headlines):
    """
    Accepte :
      - list[dict] avec clés 'title' et optionnellement 'category'
      - list[str]
      - pd.DataFrame avec colonne 'headline'
    """
    import pandas as pd
    if headlines is None:
        return

    items = ""

    if isinstance(headlines, pd.DataFrame):
        if headlines.empty:
            return
        for _, row in headlines.iterrows():
            cat  = row.get("scope") or row.get("category", "")
            text = row.get("headline", row.get("title", ""))
            if text:
                items += (
                    f'<span class="news-item">'
                    f'<span class="news-cat">{cat}</span>{text}'
                    f'</span>'
                )
    elif isinstance(headlines, list):
        if not headlines:
            return
        for h in headlines:
            if isinstance(h, dict):
                cat  = h.get("category", "")
                text = h.get("title", "")
            else:
                cat, text = "", str(h)
            if text:
                cat_html = f'<span class="news-cat">{cat}</span>' if cat else ""
                items += f'<span class="news-item">{cat_html}{text}</span>'
    else:
        return

    if not items:
        return

    double = items * 2
    st.markdown(
        f'<div class="news-wrap">'
        f'<div class="news-label">⚡ NEWS</div>'
        f'<div class="news-scroll"><div class="news-strip">{double}</div></div>'
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


def pnl_cell(value: float, suffix: str = "") -> str:
    col  = "#00ff88" if value >= 0 else "#ff3b6b"
    sign = "+" if value >= 0 else ""
    return f'<span style="color:{col};font-weight:bold;">{sign}{value:.2f}{suffix}</span>'
