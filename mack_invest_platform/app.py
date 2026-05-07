"""
McKenson Investment Platform - MIP — Main Entry Point
Run with: streamlit run app.py
"""
import streamlit as st
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

st.set_page_config(
    page_title="MIP Stock Market",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

from components.ui import inject_css, render_ticker_strip, render_news_banner
from utils.data import get_strip_data, get_or_init_state, load_events

inject_css()

# ── Sidebar navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:10px 0 20px;">
        <div style="font-family:Rajdhani,sans-serif;font-size:1.5rem;font-weight:700;
                    letter-spacing:0.15em;color:#00d4ff;">ESLSCA</div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.7rem;color:#7c3aed;
                    letter-spacing:0.2em;">STOCK MARKET GAME</div>
    </div>
    """, unsafe_allow_html=True)

    state = get_or_init_state()
    teams = state.get("teams", {})

    page = st.selectbox(
        "Navigate",
        [
            "🏠 Dashboard",
            "💼 Trading Desk",
            "📊 Technical Analysis",
            "🧮 Portfolio Optimizer",
            "🏆 Leaderboard",
            "📰 Market Events",
            "🔐 Admin Panel",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Team selector for trading
    team_options = {v["emoji"] + " " + v["name"]: k for k, v in teams.items()}
    selected_label = st.selectbox("Select Team", list(team_options.keys()))
    selected_team_id = team_options[selected_label]
    st.session_state["active_team"] = selected_team_id

    st.markdown("---")
    st.markdown(
        '<div style="font-family:Share Tech Mono,monospace;font-size:0.65rem;'
        'color:#475569;text-align:center;">v2.0 · ESLSCA · 2026</div>',
        unsafe_allow_html=True,
    )

# ── Always-on ticker strip ────────────────────────────────────────────────────
strip_data = get_strip_data()
render_ticker_strip(strip_data)

# ── Always-on news banner ─────────────────────────────────────────────────────
events_df = load_events()
active_events = events_df[events_df["active"] == True] if not events_df.empty else events_df
render_news_banner(active_events)

# ── Route to pages ────────────────────────────────────────────────────────────
if page == "🏠 Dashboard":
    from pages.dashboard import render
    render()
elif page == "💼 Trading Desk":
    from pages.trading import render
    render()
elif page == "📊 Technical Analysis":
    from pages.technical import render
    render()
elif page == "🧮 Portfolio Optimizer":
    from pages.optimizer import render
    render()
elif page == "🏆 Leaderboard":
    from pages.leaderboard import render
    render()
elif page == "📰 Market Events":
    from pages.events import render
    render()
elif page == "🔐 Admin Panel":
    from pages.admin import render
    render()
