# app.py  —  McKenson Asset Management (MAM)  v3.2
"""
Main Streamlit entry point.  Run: streamlit run app.py

FIX v3.2:
  - Hides Streamlit auto-generated multipage nav links (the list admin/dashboard/...)
  - Our selectbox IS the navigation — sits right below the MAM header
  - Sidebar: MAM header → nav dropdown → separator → team → portfolio → quick stats
"""
import importlib
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

st.set_page_config(
    page_title="MAM — McKenson Asset Management",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

from components.ui import (
    inject_css, render_indices_banner,
    render_news_banner, render_ticker_strip,
)
from utils.data import (
    get_or_init_state, get_indices_data, fetch_news_headlines,
    get_strip_data, get_multi_prices, value_portfolio,
)

inject_css()

# ── Suppress Streamlit auto-generated multipage nav list ─────────────────────
st.markdown("""
<style>
/* Hide auto-generated page links (admin, dashboard, education…) */
[data-testid="stSidebarNavItems"],
[data-testid="stSidebarNav"],
section[data-testid="stSidebar"] > div:first-child > div:first-child nav {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    overflow: hidden !important;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:

    # ── MAM Branding ───────────────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center;padding:16px 0 20px;">
      <div style="font-family:Rajdhani,sans-serif;font-size:1.8rem;font-weight:700;
           letter-spacing:.2em;color:#00d4ff;
           text-shadow:0 0 25px rgba(0,212,255,.6);">MAM</div>
      <div style="font-family:'Share Tech Mono',monospace;font-size:.62rem;
           color:#7c3aed;letter-spacing:.25em;margin-top:2px;">McKENSON ASSET MANAGEMENT</div>
      <div style="width:70%;height:1px;
           background:linear-gradient(90deg,transparent,#00d4ff,transparent);
           margin:10px auto 0;"></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Navigation selectbox (replaces the auto-links) ─────────────────────────
    PAGES = {
        "🏠  Dashboard":           "dashboard",
        "💼  Trading Desk":        "trading",
        "📊  Technical Analysis":  "technical",
        "🧮  Portfolio Optimizer": "optimizer",
        "🏆  Leaderboard":         "leaderboard",
        "📰  Events & News":       "events",
        "🎓  Education & Tools":   "education",
        "🔐  Admin Panel":         "admin",
    }
    page_label = st.selectbox(
        "Page", list(PAGES.keys()),
        label_visibility="collapsed", key="main_nav",
    )
    page_key = PAGES[page_label]

    st.markdown("---")

    # ── Team selector ──────────────────────────────────────────────────────────
    state = get_or_init_state()
    teams = state.get("teams", {})

    st.markdown(
        '<div style="font-family:Rajdhani;font-size:.7rem;color:#7a93b0;'
        'letter-spacing:.12em;text-transform:uppercase;margin-bottom:4px;">'
        'Équipe active</div>',
        unsafe_allow_html=True,
    )

    active_team = None
    active_port = None

    if teams:
        team_opts  = {f'{v["emoji"]} {v["name"]}': k for k, v in teams.items()}
        team_label = st.selectbox(
            "Team", list(team_opts.keys()),
            label_visibility="collapsed", key="sidebar_team",
        )
        active_team = team_opts[team_label]
        st.session_state["active_team"] = active_team

        # ── Portfolio selector ─────────────────────────────────────────────────
        team_data  = teams[active_team]
        portfolios = team_data.get("portfolios", {})

        # Show only portfolios that have activity; if none, show all so user can start
        used_ports = {
            k: v for k, v in portfolios.items()
            if v.get("trades") or v.get("holdings")
        }
        display_ports = used_ports if used_ports else portfolios

        st.markdown(
            '<div style="font-family:Rajdhani;font-size:.7rem;color:#7a93b0;'
            'letter-spacing:.12em;text-transform:uppercase;margin:8px 0 4px;">'
            'Portefeuille actif</div>',
            unsafe_allow_html=True,
        )
        port_opts  = {f'{v["emoji"]} {v["name"]}': k for k, v in display_ports.items()}
        port_label = st.selectbox(
            "Portfolio", list(port_opts.keys()),
            label_visibility="collapsed", key="sidebar_port",
        )
        active_port = port_opts[port_label]
        st.session_state["active_portfolio"] = active_port
    else:
        st.warning("Aucune équipe — visitez Admin.")
        st.session_state.setdefault("active_team", None)
        st.session_state.setdefault("active_portfolio", None)

    st.markdown("---")

    # ── Quick stats card ───────────────────────────────────────────────────────
    if active_team and active_port:
        p_data = teams.get(active_team, {}).get("portfolios", {}).get(active_port, {})
        if p_data:
            cash  = p_data.get("cash", 0)
            n_pos = len(p_data.get("holdings", {}))
            n_tr  = len(p_data.get("trades", []))
            init  = p_data.get("initial_cash", 1_000_000)

            tickers_ = tuple(p_data.get("holdings", {}).keys())
            prices_  = {}
            if tickers_:
                px_ = get_multi_prices(tickers_)
                prices_ = {t2: px_[t2][0] for t2 in px_}

            val_   = value_portfolio(p_data, prices_)
            total_ = val_["total"]
            pnl_   = total_ - init
            pct_   = pnl_ / init * 100 if init else 0
            col_   = "#00ff88" if pnl_ >= 0 else "#ff3b6b"
            sign_  = "+" if pnl_ >= 0 else ""

            st.markdown(
                f'<div style="background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.15);'
                f'border-radius:6px;padding:10px 12px;">'
                f'<div style="font-family:Rajdhani;font-size:.68rem;color:#7a93b0;'
                f'letter-spacing:.12em;text-transform:uppercase;margin-bottom:6px;">'
                f'{p_data.get("emoji","📊")} {p_data.get("name","")}</div>'
                f'<div style="font-family:Share Tech Mono;font-size:.73rem;color:#e2e8f0;">'
                f'Valeur <span style="color:#00d4ff;">${total_:,.0f}</span></div>'
                f'<div style="font-family:Share Tech Mono;font-size:.73rem;color:#e2e8f0;">'
                f'P&L <span style="color:{col_};">{sign_}${abs(pnl_):,.0f}'
                f' ({sign_}{abs(pct_):.2f}%)</span></div>'
                f'<div style="font-family:Share Tech Mono;font-size:.7rem;color:#7a93b0;">'
                f'Cash ${cash:,.0f} · {n_pos} pos. · {n_tr} trades</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown(
        '<div style="font-family:Share Tech Mono;font-size:.6rem;color:#334155;'
        'text-align:center;margin-top:12px;">MAM © 2026 · v3.2</div>',
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
#  LIVE BANNERS
# ══════════════════════════════════════════════════════════════════════════════

try:
    render_indices_banner(get_indices_data())
except Exception:
    pass

try:
    strip_items = get_strip_data()
    _at = st.session_state.get("active_team")
    _ap = st.session_state.get("active_portfolio")
    if _at and _ap:
        _p = teams.get(_at, {}).get("portfolios", {}).get(_ap, {})
        _h = _p.get("holdings", {})
        if _h:
            _px = get_multi_prices(tuple(_h.keys()))
            _hs = [{"ticker": t, "price": _px[t][0], "pct": _px[t][1]} for t in _h]
            _seen = {d["ticker"] for d in _hs}
            strip_items = _hs + [d for d in strip_items if d["ticker"] not in _seen]
    render_ticker_strip(strip_items)
except Exception:
    pass

try:
    render_news_banner(fetch_news_headlines())
except Exception:
    pass

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE ROUTER
# ══════════════════════════════════════════════════════════════════════════════
try:
    mod = importlib.import_module(f"pages.{page_key}")
    mod.render()
except ModuleNotFoundError as e:
    st.error(f"⚠️ Page `{page_key}` introuvable : {e}")
    st.info("Vérifiez que tous les fichiers `pages/*.py` sont présents.")
except Exception as e:
    st.exception(e)
