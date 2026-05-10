# components/ui.py  —  MAM UI components & CSS theme
"""
Dark professional theme, live banners, P&L helpers.
"""
from __future__ import annotations
import math
import streamlit as st

# ══════════════════════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════════════════════
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&family=Exo+2:wght@300;400;600;700&display=swap');

:root {
  --bg0:#030812; --bg1:#080f1e; --bg2:#0d1628; --bg3:#132035;
  --accent:#00d4ff; --accent2:#7c3aed;
  --green:#00ff88; --red:#ff3b6b; --yellow:#ffd700; --orange:#ff8c00;
  --white:#e2e8f0; --muted:#7a93b0;
  --border:rgba(0,212,255,.16); --border-red:rgba(255,59,107,.28);
  --glow:0 0 20px rgba(0,212,255,.18);
}

/* ── Base ── */
html,body,.stApp{background:var(--bg0)!important;font-family:'Exo 2',sans-serif;color:var(--white)}
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-track{background:var(--bg1)}
::-webkit-scrollbar-thumb{background:var(--accent);border-radius:2px}
h1,h2,h3{font-family:'Rajdhani',sans-serif;letter-spacing:.05em}

/* ── Sidebar ── */
section[data-testid="stSidebar"]{background:var(--bg1)!important;border-right:1px solid var(--border)}
section[data-testid="stSidebar"] label{color:var(--muted)!important;font-family:'Rajdhani',sans-serif!important;font-size:.72rem!important;letter-spacing:.1em!important;text-transform:uppercase!important}

/* ── Metrics ── */
div[data-testid="metric-container"]{background:var(--bg2)!important;border:1px solid var(--border);border-radius:8px;padding:12px!important;box-shadow:var(--glow)}

/* ── Buttons ── */
.stButton>button{background:linear-gradient(135deg,rgba(0,212,255,.1),rgba(124,58,237,.1))!important;color:var(--accent)!important;border:1px solid var(--accent)!important;border-radius:4px!important;font-family:'Rajdhani',sans-serif!important;font-weight:700!important;letter-spacing:.1em!important;text-transform:uppercase!important;transition:all .2s ease}
.stButton>button:hover{background:linear-gradient(135deg,rgba(0,212,255,.25),rgba(124,58,237,.25))!important;box-shadow:var(--glow)!important;transform:translateY(-1px)!important}

/* ── Inputs ── */
.stSelectbox>div>div,.stNumberInput>div>div>input,.stTextInput>div>div>input,.stTextArea textarea{background:var(--bg3)!important;border:1px solid var(--border)!important;color:var(--white)!important;font-family:'Share Tech Mono',monospace!important;border-radius:4px!important}
.stSlider [data-baseweb="slider"] [role="slider"]{background:var(--accent)!important}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"]{background:var(--bg1)!important;border-bottom:1px solid var(--border)}
.stTabs [data-baseweb="tab"]{color:var(--muted)!important;font-family:'Rajdhani',sans-serif!important;font-weight:700!important;font-size:.8rem!important;letter-spacing:.1em!important;text-transform:uppercase!important;padding:8px 18px!important}
.stTabs [aria-selected="true"]{color:var(--accent)!important;border-bottom:2px solid var(--accent)!important;background:rgba(0,212,255,.05)!important}

/* ── DataFrames ── */
.stDataFrame{border:1px solid var(--border)!important;border-radius:8px;overflow:hidden}

/* ── Layout ── */
div[data-testid="stVerticalBlock"]{gap:.3rem}
.block-container{padding-top:.4rem!important;padding-bottom:1rem!important;max-width:1500px}

/* ════════════════════════════════════════════
   CUSTOM COMPONENTS
═══════════════════════════════════════════ */

/* Metric card */
.mam-card{background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:14px 12px;text-align:center;box-shadow:var(--glow);transition:border-color .2s,box-shadow .2s}
.mam-card:hover{border-color:var(--accent);box-shadow:0 0 28px rgba(0,212,255,.28)}
.mam-val{font-family:'Share Tech Mono',monospace;font-size:1.35rem;color:var(--accent);font-weight:bold;line-height:1.2}
.mam-lbl{font-family:'Rajdhani',sans-serif;font-size:.67rem;color:var(--muted);letter-spacing:.12em;text-transform:uppercase;margin-bottom:5px}

/* Section title */
.mam-title{font-family:'Rajdhani',sans-serif;font-size:.95rem;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--accent);border-left:3px solid var(--accent);padding-left:10px;margin:18px 0 10px;display:flex;align-items:center}
.mam-title::after{content:'';flex:1;height:1px;background:linear-gradient(90deg,var(--border),transparent);margin-left:10px}

/* P&L classes */
.pnl-pos{color:var(--green)!important;font-family:'Share Tech Mono',monospace;font-weight:bold}
.pnl-neg{color:var(--red)!important;font-family:'Share Tech Mono',monospace;font-weight:bold}
.pnl-zero{color:var(--yellow)!important;font-family:'Share Tech Mono',monospace}

/* Badges */
.badge{display:inline-block;padding:2px 8px;border-radius:3px;font-family:'Rajdhani',sans-serif;font-size:.7rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase}
.badge-blue{background:rgba(0,212,255,.1);color:var(--accent);border:1px solid rgba(0,212,255,.3)}
.badge-green{background:rgba(0,255,136,.1);color:var(--green);border:1px solid rgba(0,255,136,.3)}
.badge-red{background:rgba(255,59,107,.1);color:var(--red);border:1px solid rgba(255,59,107,.3)}
.badge-yellow{background:rgba(255,215,0,.1);color:var(--yellow);border:1px solid rgba(255,215,0,.3)}
.badge-purple{background:rgba(124,58,237,.1);color:#a78bfa;border:1px solid rgba(124,58,237,.3)}

/* ════════════════════════════════════════════
   BANNER 1 — GLOBAL INDICES
═══════════════════════════════════════════ */
.idx-wrap{background:linear-gradient(180deg,#05101e,#03080f);border-bottom:1px solid rgba(255,215,0,.18);overflow:hidden;padding:5px 0;white-space:nowrap;position:relative;height:32px}
.idx-wrap::before,.idx-wrap::after{content:'';position:absolute;top:0;bottom:0;width:100px;z-index:2}
.idx-wrap::before{left:0;background:linear-gradient(90deg,#03080f,transparent)}
.idx-wrap::after{right:0;background:linear-gradient(-90deg,#03080f,transparent)}
.idx-lbl{position:absolute;left:0;top:0;bottom:0;display:flex;align-items:center;padding:0 14px;background:rgba(255,215,0,.08);border-right:1px solid rgba(255,215,0,.2);font-family:'Rajdhani',sans-serif;font-size:.66rem;font-weight:700;letter-spacing:.15em;color:#ffd700;z-index:3;white-space:nowrap}
.idx-scroll{display:inline-block;animation:scrollX-idx 95s linear infinite;padding-left:145px}
.idx-scroll:hover{animation-play-state:paused}
.idx-item{display:inline-block;margin:0 22px;font-family:'Share Tech Mono',monospace;font-size:.76rem}
.idx-name{color:#aabbd0;margin-right:5px}.idx-price{color:#e2e8f0}
.idx-up{color:#00ff88}.idx-dn{color:#ff3b6b}.idx-flat{color:#ffd700}
.idx-sep{color:rgba(255,215,0,.15);margin:0 8px}

/* ════════════════════════════════════════════
   BANNER 2 — LIVE NEWS
═══════════════════════════════════════════ */
.news-wrap{background:rgba(255,59,107,.04);border:1px solid rgba(255,59,107,.25);border-radius:4px;overflow:hidden;display:flex;align-items:center;height:30px;margin:4px 0 3px}
.news-lbl{flex-shrink:0;padding:0 13px;font-family:'Rajdhani',sans-serif;font-size:.68rem;font-weight:700;letter-spacing:.14em;color:#ff3b6b;border-right:1px solid rgba(255,59,107,.28);white-space:nowrap;height:100%;display:flex;align-items:center}
.news-area{overflow:hidden;flex:1;height:100%;display:flex;align-items:center}
.news-scroll{display:inline-block;animation:scrollX-news 110s linear infinite;white-space:nowrap}
.news-scroll:hover{animation-play-state:paused}
.news-item{display:inline-block;margin:0 36px;font-family:'Share Tech Mono',monospace;font-size:.73rem;color:#ff8c00}
.ncat{font-family:'Rajdhani',sans-serif;font-size:.64rem;font-weight:700;padding:1px 6px;border-radius:2px;margin-right:7px;text-transform:uppercase;letter-spacing:.08em}
.ncat-mkt{background:rgba(0,212,255,.15);color:#00d4ff}
.ncat-geo{background:rgba(255,59,107,.15);color:#ff3b6b}
.ncat-cb{background:rgba(124,58,237,.15);color:#a78bfa}
.ncat-co{background:rgba(255,215,0,.15);color:#ffd700}
.ncat-cr{background:rgba(0,255,136,.15);color:#00ff88}

/* ════════════════════════════════════════════
   BANNER 3 — PORTFOLIO TICKER
═══════════════════════════════════════════ */
.tick-wrap{background:var(--bg1);border-bottom:1px solid var(--border);border-top:1px solid var(--border);overflow:hidden;padding:5px 0;white-space:nowrap;position:relative;height:30px}
.tick-wrap::before,.tick-wrap::after{content:'';position:absolute;top:0;bottom:0;width:60px;z-index:2}
.tick-wrap::before{left:0;background:linear-gradient(90deg,var(--bg1),transparent)}
.tick-wrap::after{right:0;background:linear-gradient(-90deg,var(--bg1),transparent)}
.tick-scroll{display:inline-block;animation:scrollX-tick 55s linear infinite}
.tick-scroll:hover{animation-play-state:paused}
.tick-item{display:inline-block;margin:0 18px;font-family:'Share Tech Mono',monospace;font-size:.77rem}
.tick-up{color:var(--green)}.tick-dn{color:var(--red)}
.tick-sep{color:rgba(0,212,255,.2);margin:0 5px}

/* ── Keyframes ── */
@keyframes scrollX-idx  {0%{transform:translateX(0)}100%{transform:translateX(-50%)}}
@keyframes scrollX-news {0%{transform:translateX(0)}100%{transform:translateX(-50%)}}
@keyframes scrollX-tick {0%{transform:translateX(0)}100%{transform:translateX(-50%)}}

/* ── Table helpers ── */
.mam-table{width:100%;border-collapse:collapse}
.mam-table th{font-family:'Rajdhani',sans-serif;font-size:.68rem;color:var(--accent);letter-spacing:.1em;text-transform:uppercase;padding:8px 10px;background:rgba(0,212,255,.06);border-bottom:1px solid rgba(0,212,255,.18);text-align:left}
.mam-table td{padding:7px 10px;font-family:'Share Tech Mono',monospace;font-size:.78rem;color:var(--white);border-bottom:1px solid rgba(255,255,255,.04)}
.mam-table tr:hover td{background:rgba(0,212,255,.04)}
.mam-table-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:8px}

.positive{color:var(--green)!important}
.negative{color:var(--red)!important}
.neutral{color:var(--yellow)!important}
</style>
"""


def inject_css():
    st.markdown(_CSS, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _fp(p: float) -> str:
    """Format price intelligently."""
    if p == 0:       return "—"
    if p >= 100_000: return f"{p:,.0f}"
    if p >= 1_000:   return f"{p:,.2f}"
    if p >= 10:      return f"{p:,.2f}"
    if p >= 1:       return f"{p:,.4f}"
    return f"{p:,.5f}"


def section_title(text: str, icon: str = ""):
    prefix = f"{icon}&nbsp;" if icon else ""
    st.markdown(
        f'<div class="mam-title">{prefix}{text}</div>',
        unsafe_allow_html=True,
    )


def metric_row(metrics: list[dict]):
    """Render a row of styled metric cards."""
    if not metrics:
        return
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        with col:
            st.markdown(
                f'<div class="mam-card">'
                f'<div class="mam-lbl">{m.get("label","")}</div>'
                f'<div class="mam-val {m.get("color","")}">{m.get("value","—")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def pnl_cell(value: float, pct: float | None = None, show_dollar: bool = True) -> str:
    """Return a green/red HTML span for a P&L value."""
    cls  = "pnl-pos" if value > 0 else ("pnl-neg" if value < 0 else "pnl-zero")
    sign = "+" if value > 0 else ""
    if show_dollar:
        txt = f"{sign}${abs(value):,.2f}"
    else:
        txt = f"{sign}{abs(value):,.2f}"
    if pct is not None:
        sp  = "+" if pct > 0 else ""
        txt += f"&nbsp;({sp}{pct:.2f}%)"
    return f'<span class="{cls}">{txt}</span>'


def pct_cell(pct: float) -> str:
    cls  = "pnl-pos" if pct > 0 else ("pnl-neg" if pct < 0 else "pnl-zero")
    arr  = "▲" if pct > 0 else ("▼" if pct < 0 else "▬")
    sign = "+" if pct > 0 else ""
    return f'<span class="{cls}">{arr}&nbsp;{sign}{abs(pct):.2f}%</span>'


# ══════════════════════════════════════════════════════════════════════════════
#  BANNER 1 — GLOBAL INDICES
# ══════════════════════════════════════════════════════════════════════════════

def render_indices_banner(indices: list[dict]):
    if not indices:
        return
    items = ""
    for q in indices:
        p   = q.get("price", 0.0)
        pct = q.get("pct", 0.0)
        cls = "idx-up" if pct > 0.04 else ("idx-dn" if pct < -0.04 else "idx-flat")
        arr = "▲" if pct > 0.04 else ("▼" if pct < -0.04 else "▬")
        items += (
            f'<span class="idx-item">'
            f'<span class="idx-name">{q["emoji"]}&nbsp;{q["name"]}</span>'
            f'<span class="idx-price">{_fp(p)}</span>'
            f'&nbsp;<span class="{cls}">{arr}&nbsp;{abs(pct):.2f}%</span>'
            f'</span><span class="idx-sep">◆</span>'
        )
    html = items * 2
    st.markdown(
        f'<div class="idx-wrap">'
        f'<div class="idx-lbl">🌐&nbsp;MARCHÉS</div>'
        f'<div class="idx-scroll">{html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  BANNER 2 — LIVE NEWS
# ══════════════════════════════════════════════════════════════════════════════

_CAT_MAP = {
    "Markets":       "ncat-mkt",
    "Geopolitics":   "ncat-geo",
    "Central Banks": "ncat-cb",
    "Commodities":   "ncat-co",
    "Crypto":        "ncat-cr",
    "Earnings":      "ncat-mkt",
    "Macro":         "ncat-cb",
}


def render_news_banner(headlines: list[dict]):
    if not headlines:
        return
    items = ""
    for h in headlines:
        cat   = h.get("category", "Markets")
        ccls  = _CAT_MAP.get(cat, "ncat-mkt")
        title = h.get("title", "")[:110]
        items += (
            f'<span class="news-item">'
            f'<span class="ncat {ccls}">{cat}</span>'
            f'{title}'
            f'</span>'
        )
    html = items * 2
    st.markdown(
        f'<div class="news-wrap">'
        f'<div class="news-lbl">📡&nbsp;LIVE&nbsp;NEWS</div>'
        f'<div class="news-area"><div class="news-scroll">{html}</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  BANNER 3 — PORTFOLIO ASSET TICKER
# ══════════════════════════════════════════════════════════════════════════════

def render_ticker_strip(items: list[dict]):
    if not items:
        return
    html = ""
    for d in items:
        pct = d.get("pct", 0.0)
        cls = "tick-up" if pct >= 0 else "tick-dn"
        arr = "▲" if pct >= 0 else "▼"
        html += (
            f'<span class="tick-item">'
            f'<b style="color:#e2e8f0;">{d["ticker"]}</b>&nbsp;'
            f'<span style="color:#94a3b8;">{_fp(d["price"])}</span>&nbsp;'
            f'<span class="{cls}">{arr}&nbsp;{abs(pct):.2f}%</span>'
            f'</span>'
            f'<span class="tick-sep">|</span>'
        )
    html2 = html * 2
    st.markdown(
        f'<div class="tick-wrap"><div class="tick-scroll">{html2}</div></div>',
        unsafe_allow_html=True,
    )
