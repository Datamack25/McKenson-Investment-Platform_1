# app.py  —  McKenson Asset Management (MAM)  v3.0
"""
Main Streamlit entry point.
Run: streamlit run app.py
"""
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

# ── Core imports ───────────────────────────────────────────────────────────────
from components.ui import (
    inject_css, render_indices_banner,
    render_news_banner, render_ticker_strip,
)
from utils.data import (
    get_or_init_state, get_indices_data,
    fetch_news_headlines, load_assets, get_multi_prices,
)

inject_css()

# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
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
    """, unsafe_allow_html=True)

    # ── Navigation ─────────────────────────────────────────────────────────────
    PAGES = {
        "🏠  Dashboard":             "dashboard",
        "💼  Trading Desk":          "trading",
        "📊  Technical Analysis":    "technical",
        "🧮  Portfolio Optimizer":   "optimizer",
        "🏆  Leaderboard":           "leaderboard",
        "📰  Events & News":         "events",
        "🎓  Education & Tools":     "education",
        "🔐  Admin Panel":           "admin",
    }
    page_label = st.selectbox(
        "Navigation", list(PAGES.keys()),
        label_visibility="collapsed",
    )
    page_key = PAGES[page_label]

    st.markdown("---")

    # ── Team / Portfolio selector ───────────────────────────────────────────────
    state = get_or_init_state()
    teams = state.get("teams", {})

    if teams:
        team_opts = {f'{v["emoji"]} {v["name"]}': k for k, v in teams.items()}
        team_label = st.selectbox(
            "Équipe active", list(team_opts.keys()),
            label_visibility="visible",
            key="sidebar_team",
        )
        active_team = team_opts[team_label]
        st.session_state["active_team"] = active_team

        # Portfolio selector within the team
        team_data = teams[active_team]
        portfolios = team_data.get("portfolios", {})
        if portfolios:
            port_opts = {f'{v["emoji"]} {v["name"]}': k
                         for k, v in portfolios.items()}
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
    else:
        st.warning("Aucune équipe. Visitez Admin.")
        st.session_state.setdefault("active_team", None)
        st.session_state.setdefault("active_portfolio", None)

    st.markdown("---")

    # ── Quick stats mini-card ───────────────────────────────────────────────────
    active_team_id  = st.session_state.get("active_team")
    active_port_id  = st.session_state.get("active_portfolio")
    if active_team_id and active_port_id:
        t  = teams.get(active_team_id, {})
        p  = t.get("portfolios", {}).get(active_port_id, {})
        cash    = p.get("cash", 0)
        n_pos   = len(p.get("holdings", {}))
        n_tr    = len(p.get("trades", []))
        init    = p.get("initial_cash", 1_000_000)
        from utils.data import value_portfolio, get_multi_prices as gmp
        tickers = tuple(p.get("holdings", {}).keys())
        _px     = gmp(tickers) if tickers else {}
        val     = value_portfolio(p, {t2: _px[t2][0] for t2 in _px})
        total   = val["total"]
        pnl     = total - init
        pnl_pct = pnl / init * 100 if init else 0
        pnl_col = "#00ff88" if pnl >= 0 else "#ff3b6b"
        sign    = "+" if pnl >= 0 else ""
        st.markdown(
            f'<div style="background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.15);'
            f'border-radius:6px;padding:10px 12px;font-family:Share Tech Mono,monospace;'
            f'font-size:.73rem;">'
            f'<div style="color:#7a93b0;font-family:Rajdhani;font-size:.68rem;'
            f'letter-spacing:.12em;text-transform:uppercase;margin-bottom:6px;">'
            f'{p.get("name","Portefeuille")}</div>'
            f'<div style="color:#e2e8f0;">Valeur&nbsp;<span style="color:#00d4ff;">'
            f'${total:,.0f}</span></div>'
            f'<div style="color:#e2e8f0;">P&L&nbsp;<span style="color:{pnl_col};">'
            f'{sign}${pnl:,.0f} ({sign}{pnl_pct:.2f}%)</span></div>'
            f'<div style="color:#7a93b0;">Cash&nbsp;${cash:,.0f}&nbsp;·&nbsp;'
            f'{n_pos} pos.&nbsp;·&nbsp;{n_tr} trades</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        '<div style="font-family:Share Tech Mono;font-size:.6rem;color:#334155;'
        'text-align:center;margin-top:12px;">MAM © 2026 · v3.0</div>',
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
#  LIVE BANNERS  (always visible, cached)
# ══════════════════════════════════════════════════════════════════════════════
indices   = get_indices_data()
headlines = fetch_news_headlines()

render_indices_banner(indices)

# Game asset ticker (top positions across portfolios)
_all_tickers = set()
for _tm in state.get("teams", {}).values():
    for _pt in _tm.get("portfolios", {}).values():
        _all_tickers.update(_pt.get("holdings", {}).keys())

if _all_tickers:
    _px2 = get_multi_prices(tuple(_all_tickers))
    _strip = [{"ticker": t, "price": _px2[t][0], "pct": _px2[t][1]}
              for t in sorted(_all_tickers)]
    render_ticker_strip(_strip)

render_news_banner(headlines)

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE ROUTER
# ══════════════════════════════════════════════════════════════════════════════
import importlib
try:
    mod = importlib.import_module(f"pages.{page_key}")
    mod.render()
except ModuleNotFoundError as e:
    st.error(f"Page `{page_key}` introuvable : {e}")
except Exception as e:
    st.exception(e)
