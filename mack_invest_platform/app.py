import streamlit as st
import pandas as pd
import numpy as np
import time
import threading
from datetime import datetime

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MAM — McKenson Asset Management",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Share+Tech+Mono&display=swap');

html, body, [data-testid="stApp"] {
    background: #080e1a !important;
    color: #e2e8f0 !important;
    font-family: 'Share Tech Mono', monospace;
}

/* ── Sidebar toggle — toujours visible ── */
[data-testid="stSidebarCollapseButton"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
}
[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: rgba(8,14,26,0.98) !important;
    border-right: 1px solid rgba(0,212,255,0.1) !important;
}

/* ── Ticker bandeaux — inline dans le flux, pas fixed ── */
.ticker-wrapper {
    width: 100%;
    margin: 0 0 18px 0;
    background: transparent;
}

.ticker-band {
    width: 100%;
    height: 24px;
    overflow: hidden;
    background: rgba(0,8,18,0.95);
    border: 1px solid rgba(0,212,255,0.14);
    border-radius: 4px;
    display: flex;
    align-items: center;
    margin-bottom: 4px;
}

.ticker-band.news-band {
    background: rgba(4,4,16,0.95);
    border-color: rgba(124,58,237,0.18);
    margin-bottom: 0;
}

.ticker-track {
    display: flex;
    white-space: nowrap;
    animation: ticker-scroll 60s linear infinite;
}

.ticker-track.news-track {
    animation: ticker-scroll 90s linear infinite;
}

@keyframes ticker-scroll {
    0%   { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}

.ticker-item {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 0 14px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.64rem;
    color: #94a3b8;
    border-right: 1px solid rgba(255,255,255,0.05);
}

.ticker-item .sym {
    color: #00d4ff;
    font-weight: 700;
    font-size: 0.63rem;
    letter-spacing: 0.04em;
}

.ticker-item .px  { color: #e2e8f0; font-size: 0.64rem; }
.ticker-item .up  { color: #00ff88; font-size: 0.61rem; }
.ticker-item .down{ color: #ff3b6b; font-size: 0.61rem; }

.news-item {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 0 18px;
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.68rem;
    color: #7a93b0;
    letter-spacing: 0.03em;
    border-right: 1px solid rgba(255,255,255,0.04);
}

.news-item .tag {
    color: #7c3aed;
    font-weight: 700;
    font-size: 0.61rem;
    letter-spacing: 0.1em;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg,rgba(0,212,255,.12),rgba(124,58,237,.12)) !important;
    border: 1px solid rgba(0,212,255,.3) !important;
    color: #00d4ff !important;
    font-family: 'Rajdhani',sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: .08em !important;
    border-radius: 4px !important;
    transition: all .2s !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg,rgba(0,212,255,.25),rgba(124,58,237,.25)) !important;
    border-color: rgba(0,212,255,.6) !important;
    box-shadow: 0 0 16px rgba(0,212,255,.25) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid rgba(0,212,255,.1) !important;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Rajdhani',sans-serif !important;
    font-weight: 700 !important;
    font-size: .78rem !important;
    letter-spacing: .1em !important;
    color: #475569 !important;
    border-bottom: 2px solid transparent !important;
    padding: 8px 16px !important;
}
.stTabs [aria-selected="true"] {
    color: #00d4ff !important;
    border-bottom-color: #00d4ff !important;
    background: rgba(0,212,255,.04) !important;
}

/* PnL colours */
.pnl-pos  { color: #00ff88 !important; }
.pnl-neg  { color: #ff3b6b !important; }
.pnl-zero { color: #94a3b8 !important; }

/* Selectbox / inputs */
[data-testid="stSelectbox"] > div > div,
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input {
    background: rgba(0,10,30,.6) !important;
    border: 1px solid rgba(0,212,255,.2) !important;
    color: #e2e8f0 !important;
    font-family: 'Share Tech Mono',monospace !important;
    border-radius: 4px !important;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: rgba(0,212,255,.04) !important;
    border: 1px solid rgba(0,212,255,.12) !important;
    border-radius: 6px !important;
    padding: 10px 14px !important;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    background: rgba(0,10,25,.5) !important;
    border: 1px solid rgba(0,212,255,.12) !important;
    border-radius: 6px !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: rgba(0,0,0,.2); }
::-webkit-scrollbar-thumb { background: rgba(0,212,255,.3); border-radius: 2px; }

/* Hide streamlit default header content — mais garder le bouton collapse sidebar */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }

/* On cache le header visuellement mais on garde sa hauteur pour le bouton collapse */
[data-testid="stHeader"] {
    background: transparent !important;
    border-bottom: none !important;
    box-shadow: none !important;
}
/* On masque tout dans le header SAUF le bouton collapse */
[data-testid="stHeader"] > *:not([data-testid="stSidebarCollapseButton"]):not([data-testid="collapsedControl"]) {
    visibility: hidden !important;
}

/* Bouton collapse sidebar — toujours bien visible */
[data-testid="stSidebarCollapseButton"] {
    visibility: visible !important;
    display: flex !important;
    opacity: 1 !important;
    background: rgba(0,212,255,.08) !important;
    border: 1px solid rgba(0,212,255,.25) !important;
    border-radius: 6px !important;
}
[data-testid="stSidebarCollapseButton"]:hover {
    background: rgba(0,212,255,.18) !important;
    border-color: rgba(0,212,255,.5) !important;
}
[data-testid="stSidebarCollapseButton"] svg {
    fill: #00d4ff !important;
    stroke: #00d4ff !important;
}
/* Bouton quand sidebar est fermée */
[data-testid="collapsedControl"] {
    visibility: visible !important;
    display: flex !important;
    opacity: 1 !important;
    background: rgba(0,212,255,.08) !important;
    border: 1px solid rgba(0,212,255,.25) !important;
    border-radius: 6px !important;
    z-index: 1200 !important;
}
[data-testid="collapsedControl"] svg {
    fill: #00d4ff !important;
    stroke: #00d4ff !important;
}

/* Masquer nav auto Streamlit multi-pages */
[data-testid="stSidebarNav"] { display: none !important; }
section[data-testid="stSidebar"] ul { display: none !important; }

/* Sidebar portfolio summary card */
.port-summary-card {
    background: rgba(0,212,255,.04);
    border: 1px solid rgba(0,212,255,.12);
    border-radius: 7px;
    padding: 9px 12px;
    margin: 5px 0;
    font-family: 'Share Tech Mono', monospace;
    font-size: .68rem;
}
.port-summary-card .port-name {
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: .82rem;
    color: #e2e8f0;
    margin-bottom: 4px;
}
.port-summary-card .port-stat {
    color: #7a93b0;
    line-height: 1.7;
}
.sidebar-section-label {
    font-family: 'Rajdhani', sans-serif;
    font-size: .62rem;
    color: #334155;
    letter-spacing: .16em;
    text-transform: uppercase;
    margin: 10px 0 4px;
}
</style>
""", unsafe_allow_html=True)

# ── Ticker data ────────────────────────────────────────────────────────────────
TICKER_SYMBOLS = [
    "AAPL","MSFT","GOOGL","AMZN","NVDA","TSLA","META","BRK-B","JPM","V",
    "BTC-USD","ETH-USD","GC=F","CL=F","EURUSD=X","^SPX","^IXIC","^DJI",
    "NFLX","AMD","INTC","BAC","WMT","XOM","CVX","LLY","UNH","PFE",
]

NEWS_ITEMS = [
    ("MACRO","Fed maintient les taux entre 5.25%-5.50%"),
    ("TECH","NVIDIA dépasse les 1 000 Mds de capitalisation"),
    ("CRYPTO","Bitcoin teste les 70 000$ — halving en vue"),
    ("ENERGY","Le pétrole WTI recule sous 80$ le baril"),
    ("FX","EUR/USD se stabilise autour de 1.085"),
    ("MACRO","PMI Zone Euro surprend à la hausse à 51.2"),
    ("TECH","Apple annonce un rachat d'actions de 110 Mds$"),
    ("BONDS","Le 10 ans US remonte à 4.35%"),
    ("MACRO","Inflation US CPI à +3.2% sur 12 mois"),
    ("ASIA","Nikkei franchit 40 000 pts pour la première fois"),
    ("CRYPTO","ETF Bitcoin Spot approuvé par la SEC"),
    ("ENERGY","GNL européen : prix en forte baisse ce trimestre"),
]


@st.cache_data(ttl=60)
def fetch_ticker_prices(symbols):
    try:
        import yfinance as yf
        data = yf.download(symbols, period="2d", interval="1d",
                           auto_adjust=True, progress=False)
        results = {}
        if "Close" in data.columns:
            closes = data["Close"]
            for sym in symbols:
                try:
                    col = closes[sym] if sym in closes.columns else closes
                    vals = col.dropna()
                    if len(vals) >= 2:
                        px   = float(vals.iloc[-1])
                        prev = float(vals.iloc[-2])
                        pct  = (px - prev) / prev * 100 if prev else 0.0
                        results[sym] = (px, pct)
                    elif len(vals) == 1:
                        results[sym] = (float(vals.iloc[-1]), 0.0)
                except Exception:
                    pass
        return results
    except Exception:
        return {}


def build_ticker_html(prices: dict) -> str:
    items = ""
    for sym in TICKER_SYMBOLS:
        if sym not in prices:
            continue
        px, pct = prices[sym]
        arr  = "▲" if pct >= 0 else "▼"
        cls  = "up" if pct >= 0 else "down"
        sign = "+" if pct >= 0 else ""
        disp = sym.replace("-USD","").replace("=X","").replace("=F","").replace("^","")
        if px >= 1000:
            px_str = f"${px:,.0f}"
        elif px >= 1:
            px_str = f"${px:,.2f}"
        else:
            px_str = f"${px:,.4f}"
        items += (
            f'<span class="ticker-item">'
            f'<span class="sym">{disp}</span>'
            f'<span class="px">{px_str}</span>'
            f'<span class="{cls}">{arr}{sign}{abs(pct):.2f}%</span>'
            f'</span>'
        )
    # duplicate for seamless loop
    return items + items


def build_news_html() -> str:
    items = ""
    for tag, text in NEWS_ITEMS:
        items += (
            f'<span class="news-item">'
            f'<span class="tag">[{tag}]</span>'
            f'{text}'
            f'</span>'
        )
    return items + items


# ── Render bandeaux ────────────────────────────────────────────────────────────
prices = fetch_ticker_prices(TICKER_SYMBOLS)
ticker_html = build_ticker_html(prices)
news_html   = build_news_html()

st.markdown(f"""
<div class="ticker-wrapper">
  <div class="ticker-band">
    <div class="ticker-track">{ticker_html}</div>
  </div>
  <div class="ticker-band news-band">
    <div class="ticker-track news-track">{news_html}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Initialise session state ───────────────────────────────────────────────────
from utils.data import get_or_init_state, persist

state = get_or_init_state()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:

    # ── Logo MAM ──────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center;padding:18px 0 12px;">
      <div style="font-family:Rajdhani,sans-serif;font-size:2rem;font-weight:700;
                  color:#00ff88;letter-spacing:.22em;
                  text-shadow:0 0 28px rgba(0,255,136,.5),0 0 8px rgba(0,255,136,.2);">
        MAM
      </div>
      <div style="font-family:Rajdhani,sans-serif;font-size:.58rem;color:#334155;
                  letter-spacing:.26em;text-transform:uppercase;margin-top:2px;">
        McKenson Asset Management
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr style="border:none;border-top:1px solid rgba(0,212,255,.1);margin:0 0 10px;">', unsafe_allow_html=True)

    # ── Sélecteurs équipe / portefeuille ──────────────────────────────────────
    teams = state.get("teams", {})
    team_names = {tid: t["name"] for tid, t in teams.items()}

    if team_names:
        sel_team = st.selectbox(
            "🏢 Équipe",
            list(team_names.keys()),
            format_func=lambda x: team_names[x],
            key="active_team",
        )
    else:
        st.caption("Aucune équipe — créez-en une via Gestion des Équipes.")
        sel_team = None
        st.session_state["active_team"] = None

    if sel_team:
        team_ports = teams[sel_team].get("portfolios", {})
        user_ports = {
            pid: p for pid, p in team_ports.items()
            if p.get("name")
        }
        if user_ports:
            port_labels = {
                pid: f'{p.get("emoji","📁")} {p["name"]}'
                for pid, p in user_ports.items()
            }
            st.selectbox(
                "📂 Portefeuille",
                list(port_labels.keys()),
                format_func=lambda x: port_labels[x],
                key="active_portfolio",
            )
        else:
            st.caption("Aucun portefeuille — créez-en un dans Portfolios.")
            st.session_state["active_portfolio"] = None

    # ── Résumé rapide des portefeuilles ───────────────────────────────────────
    if sel_team and user_ports:
        try:
            from utils.data import get_multi_prices as _gmp

            st.markdown(
                f'<div class="sidebar-section-label">'
                f'📊 {len(user_ports)} portefeuille(s) actif(s)</div>',
                unsafe_allow_html=True,
            )

            for pid, port in list(user_ports.items())[:4]:  # max 4 cards
                holdings = port.get("holdings", {})
                cash     = port.get("cash", 0.0)
                name     = port.get("name", "—")
                emoji    = port.get("emoji", "📁")
                ptype    = port.get("portfolio_type", "Libre")

                mkt_val = 0.0
                pnl     = 0.0
                n_pos   = len(holdings)

                if holdings:
                    prices_snap = _gmp(tuple(holdings.keys()))
                    for tk, pos in holdings.items():
                        qty  = pos.get("qty", 0)
                        avg  = pos.get("avg_price", 0.0)
                        curr, _ = prices_snap.get(tk, (avg, 0.0))
                        mkt_val += qty * curr
                        pnl     += qty * (curr - avg)

                total_aum = cash + mkt_val
                pnl_col   = "#00ff88" if pnl >= 0 else "#ff3b6b"
                pnl_sign  = "+" if pnl >= 0 else ""
                pnl_pct   = (pnl / (mkt_val - pnl) * 100) if (mkt_val - pnl) > 0 else 0.0

                is_active = (pid == st.session_state.get("active_portfolio"))
                border_col = "rgba(0,212,255,.35)" if is_active else "rgba(0,212,255,.1)"

                st.markdown(
                    f'<div class="port-summary-card" style="border-color:{border_col};">'
                    f'<div class="port-name">{emoji} {name}'
                    f'<span style="font-family:Rajdhani;font-size:.6rem;color:#334155;'
                    f'margin-left:6px;letter-spacing:.1em;">{ptype}</span></div>'
                    f'<div class="port-stat">'
                    f'AUM <b style="color:#e2e8f0;">${total_aum:,.0f}</b> &nbsp;·&nbsp; '
                    f'{n_pos} pos.<br>'
                    f'P&L <b style="color:{pnl_col};">{pnl_sign}${abs(pnl):,.2f}'
                    f'</b> <span style="color:{pnl_col};font-size:.62rem;">'
                    f'({pnl_sign}{abs(pnl_pct):.2f}%)</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
        except Exception:
            pass

    st.markdown('<hr style="border:none;border-top:1px solid rgba(0,212,255,.1);margin:10px 0 8px;">', unsafe_allow_html=True)

    # ── Navigation ────────────────────────────────────────────────────────────
    pages = {
        "🏠 Dashboard":           "dashboard",
        "📁 Portfolios":          "portfolios",
        "💼 Trading Desk":        "trading",
        "📊 Analytics":           "analytics",
        "🏆 Classement":          "ranking",
        "🏢 Gestion des Équipes": "teams",
        "⚙️ Paramètres":          "settings",
    }
    if "page" not in st.session_state:
        st.session_state["page"] = "dashboard"

    for label, key in pages.items():
        active = st.session_state["page"] == key
        if st.button(label, key=f"nav_{key}", use_container_width=True):
            st.session_state["page"] = key
            st.rerun()

    st.markdown('<hr style="border:none;border-top:1px solid rgba(0,212,255,.08);margin:8px 0 6px;">', unsafe_allow_html=True)

    # Horloge
    st.markdown(
        f'<div style="text-align:center;font-family:Share Tech Mono;font-size:.62rem;'
        f'color:#283347;padding-bottom:6px;">'
        f'{datetime.now().strftime("%d/%m/%Y  %H:%M")}</div>',
        unsafe_allow_html=True,
    )

# ── Page routing ───────────────────────────────────────────────────────────────
page = st.session_state.get("page", "dashboard")

if page == "dashboard":
    from pages import dashboard
    dashboard.render()
elif page == "portfolios":
    from pages import portfolios
    portfolios.render()
elif page == "trading":
    from pages import trading
    trading.render()
elif page == "analytics":
    from pages import analytics
    analytics.render()
elif page == "ranking":
    from pages import ranking
    ranking.render()
elif page == "teams":
    from pages import teams as teams_page
    teams_page.render()
elif page == "settings":
    from pages import settings
    settings.render()
