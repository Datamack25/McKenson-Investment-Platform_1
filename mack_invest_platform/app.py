"""
ESLSCA Stock Market Game — Main Entry Point
Run with:  streamlit run app.py
"""
import streamlit as st
import sys
from pathlib import Path

# Ensure project root is on the Python path
sys.path.insert(0, str(Path(__file__).parent))

st.set_page_config(
    page_title="ESLSCA · Stock Market Game",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

from components.ui import inject_css, render_ticker_strip, render_news_banner
from utils.data import get_strip_data, get_or_init_state, load_events

inject_css()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center;padding:14px 0 22px;">
            <div style="
                font-family:Rajdhani,sans-serif;
                font-size:1.7rem;
                font-weight:700;
                letter-spacing:0.2em;
                color:#00d4ff;
                text-shadow:0 0 20px rgba(0,212,255,0.6);
            ">ESLSCA</div>
            <div style="
                font-family:'Share Tech Mono',monospace;
                font-size:0.65rem;
                color:#7c3aed;
                letter-spacing:0.25em;
                margin-top:2px;
            ">STOCK MARKET GAME · v2.1</div>
            <div style="
                width:60%;
                height:1px;
                background:linear-gradient(90deg,transparent,#00d4ff,transparent);
                margin:12px auto 0;
            "></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    state = get_or_init_state()
    teams = state.get("teams", {})

    PAGES = [
        "🏠 Dashboard",
        "💼 Trading Desk",
        "📊 Technical Analysis",
        "🧮 Portfolio Optimizer",
        "🏆 Leaderboard",
        "📰 Market Events",
        "🔐 Admin Panel",
    ]

    page = st.selectbox("Navigate", PAGES, label_visibility="collapsed")

    st.markdown(
        '<div style="font-family:Rajdhani;font-size:0.7rem;color:#475569;'
        'letter-spacing:0.1em;text-transform:uppercase;margin:8px 0 4px;">Active Team</div>',
        unsafe_allow_html=True,
    )

    if teams:
        team_options = {f'{v["emoji"]} {v["name"]}': k for k, v in teams.items()}
        selected_label = st.selectbox(
            "Select Team",
            list(team_options.keys()),
            label_visibility="collapsed",
        )
        st.session_state["active_team"] = team_options[selected_label]
    else:
        st.warning("No teams found. Visit Admin Panel.")
        st.session_state.setdefault("active_team", None)

    st.markdown("---")

    # Quick team stats mini-widget
    active_team_id = st.session_state.get("active_team")
    if active_team_id and active_team_id in teams:
        t = teams[active_team_id]
        cash = t.get("cash", 0)
        n_positions = len(t.get("holdings", {}))
        n_trades = len(t.get("trades", []))
        st.markdown(
            f'<div style="background:rgba(0,212,255,0.05);border:1px solid rgba(0,212,255,0.15);'
            f'border-radius:6px;padding:10px 12px;font-family:Share Tech Mono,monospace;font-size:0.73rem;">'
            f'<div style="color:#7a93b0;margin-bottom:4px;font-family:Rajdhani,sans-serif;'
            f'font-size:0.7rem;letter-spacing:0.12em;text-transform:uppercase;">Quick Stats</div>'
            f'<div style="color:#e2e8f0;">💵 Cash &nbsp;<span style="color:#00d4ff;">${cash:,.0f}</span></div>'
            f'<div style="color:#e2e8f0;">📦 Positions &nbsp;<span style="color:#00d4ff;">{n_positions}</span></div>'
            f'<div style="color:#e2e8f0;">🔄 Trades &nbsp;<span style="color:#00d4ff;">{n_trades}</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Always-on ticker strip ────────────────────────────────────────────────────
strip_data = get_strip_data()
render_ticker_strip(strip_data)

# ── Always-on news banner ─────────────────────────────────────────────────────
events_df = load_events()
if not events_df.empty and "active" in events_df.columns:
    active_events = events_df[events_df["active"] == True]
else:
    active_events = events_df
render_news_banner(active_events)

# ── Route to pages ────────────────────────────────────────────────────────────
page_map = {
    "🏠 Dashboard":           ("pages.dashboard",   "render"),
    "💼 Trading Desk":        ("pages.trading",     "render"),
    "📊 Technical Analysis":  ("pages.technical",   "render"),
    "🧮 Portfolio Optimizer": ("pages.optimizer",   "render"),
    "🏆 Leaderboard":         ("pages.leaderboard", "render"),
    "📰 Market Events":       ("pages.events",      "render"),
    "🔐 Admin Panel":         ("pages.admin",       "render"),
}

if page in page_map:
    module_path, func_name = page_map[page]
    try:
        import importlib
        mod = importlib.import_module(module_path)
        getattr(mod, func_name)()
    except ModuleNotFoundError as e:
        st.error(f"⚠️ Page module not found: `{module_path}` — {e}")
    except AttributeError:
        st.error(f"⚠️ Function `{func_name}` not found in `{module_path}`.")
    except Exception as e:
        st.exception(e)
else:
    st.error(f"Unknown page: {page}")
