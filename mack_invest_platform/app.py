# app.py  —  McKenson Asset Management (MAM)  v3.1  FIXED
"""
Main Streamlit entry point.
Run: streamlit run app.py

FIX v3.1:
  - Banners (indices + news + ticker) now render AFTER sidebar & BEFORE page content
  - Uses correct function names from utils.data
  - Robust team/portfolio session-state handling
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
    inject_css,
    render_indices_banner,
    render_news_banner,
    render_ticker_strip,
)
from utils.data import (
    get_or_init_state,
    get_indices_data,
    fetch_news_headlines,
    get_strip_data,
    get_multi_prices,
    value_portfolio,
)

inject_css()

# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center;padding:16px 0 24px;">
          <div style="font-family:Rajdhani,sans-serif;font-size:1.8rem;font-weight:700;
               letter-spacing:.2em;color:#00d4ff;
               text-shadow:0 0 25px rgba(0,212,255,.6);">MAM</div>
          <div style="font-family:'Share Tech Mono',monospace;font-size:.62rem;
               color:#7c3aed;letter-spacing:.25em;margin-top:2px;">
               McKENSON ASSET MANAGEMENT</div>
          <div style="width:70%;height:1px;
               background:linear-gradient(90deg,transparent,#00d4ff,transparent);
               margin:12px auto 0;"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Navigation ─────────────────────────────────────────────────────────────
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
        "Navigation", list(PAGES.keys()),
        label_visibility="collapsed",
    )
    page_key = PAGES[page_label]

    st.markdown("---")

    # ── Team selector ──────────────────────────────────────────────────────────
    state = get_or_init_state()
    teams = state.get("teams", {})

    if teams:
        team_opts  = {f'{v["emoji"]} {v["name"]}': k for k, v in teams.items()}
        team_label = st.selectbox(
            "Équipe active", list(team_opts.keys()),
            label_visibility="visible",
            key="sidebar_team",
        )
        active_team = team_opts[team_label]
        st.session_state["active_team"] = active_team

        # ── Portfolio selector ─────────────────────────────────────────────────
        team_data  = teams[active_team]
        portfolios = team_data.get("portfolios", {})
        if portfolios:
            port_opts  = {
                f'{v["emoji"]} {v["name"]}': k
                for k, v in portfolios.items()
            }
            port_label = st.selectbox(
                "Portefeuille actif", list(port_opts.keys()),
                label_visibility="visible",
                key="sidebar_port",
            )
            active_port = port_opts[port_label]
            st.session_state["active_portfolio"] = active_port
        else:
            st.info("Aucun portefeuille — créez-en un dans Admin.")
            st.session_state["active_portfolio"] = None
            active_port = None
    else:
        st.warning("Aucune équipe. Visitez Admin.")
        st.session_state.setdefault("active_team", None)
        st.session_state.setdefault("active_portfolio", None)
        active_team = None
        active_port = None

    st.markdown("---")

    # ── Quick stats mini-card ───────────────────────────────────────────────────
    if active_team and active_port:
        t_data = teams.get(active_team, {})
        p_data = t_data.get("portfolios", {}).get(active_port, {})
        if p_data:
            cash   = p_data.get("cash", 0)
            n_pos  = len(p_data.get("holdings", {}))
            n_tr   = len(p_data.get("trades", []))
            init   = p_data.get("initial_cash", 1_000_000)

            # Light valuation for sidebar
            holdings = p_data.get("holdings", {})
            tickers_ = tuple(holdings.keys())
            if tickers_:
                px_ = get_multi_prices(tickers_)
                prices_ = {t2: px_[t2][0] for t2 in px_}
            else:
                prices_ = {}
            val_   = value_portfolio(p_data, prices_)
            total_ = val_["total"]
            pnl_   = total_ - init
            pct_   = pnl_ / init * 100 if init else 0
            col_   = "#00ff88" if pnl_ >= 0 else "#ff3b6b"
            sign_  = "+" if pnl_ >= 0 else ""

            st.markdown(
                f'<div style="background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.15);'
                f'border-radius:6px;padding:10px 12px;font-family:Share Tech Mono,monospace;'
                f'font-size:.73rem;">'
                f'<div style="color:#7a93b0;font-family:Rajdhani;font-size:.68rem;'
                f'letter-spacing:.12em;text-transform:uppercase;margin-bottom:6px;">'
                f'{p_data.get("emoji","")} {p_data.get("name","")}</div>'
                f'<div style="color:#e2e8f0;">Valeur&nbsp;'
                f'<span style="color:#00d4ff;">${total_:,.0f}</span></div>'
                f'<div style="color:#e2e8f0;">P&L&nbsp;'
                f'<span style="color:{col_};">{sign_}${abs(pnl_):,.0f} ({sign_}{abs(pct_):.2f}%)</span></div>'
                f'<div style="color:#7a93b0;">Cash&nbsp;${cash:,.0f}'
                f'&nbsp;·&nbsp;{n_pos}&nbsp;pos.'
                f'&nbsp;·&nbsp;{n_tr}&nbsp;trades</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown(
        '<div style="font-family:Share Tech Mono;font-size:.6rem;color:#334155;'
        'text-align:center;margin-top:12px;">MAM © 2026 · v3.1</div>',
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
#  LIVE BANNERS  — rendered AFTER sidebar, BEFORE page content
#  This placement guarantees they appear at the top of the main area.
# ══════════════════════════════════════════════════════════════════════════════

# Banner 1 — Global indices (NASDAQ, S&P, CAC, Gold, BTC …)
try:
    indices = get_indices_data()
    render_indices_banner(indices)
except Exception:
    pass

# Banner 2 — Portfolio asset ticker strip (holdings of active portfolio)
try:
    # Always show major market ticker even if no holdings
    strip_items = get_strip_data()

    # If team has active portfolio, prepend its holdings
    if active_team and active_port:
        p_data   = teams.get(active_team, {}).get("portfolios", {}).get(active_port, {})
        holdings = p_data.get("holdings", {})
        if holdings:
            tickers_h = tuple(holdings.keys())
            px_h      = get_multi_prices(tickers_h)
            holding_strip = [
                {"ticker": t, "price": px_h[t][0], "pct": px_h[t][1]}
                for t in tickers_h
            ]
            # Merge: holdings first, then market strip (deduplicated by ticker)
            seen = {d["ticker"] for d in holding_strip}
            extra = [d for d in strip_items if d["ticker"] not in seen]
            strip_items = holding_strip + extra

    render_ticker_strip(strip_items)
except Exception:
    pass

# Banner 3 — Live news headlines
try:
    headlines = fetch_news_headlines()
    render_news_banner(headlines)
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
