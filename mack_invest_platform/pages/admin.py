"""
Admin Panel: manage teams, events, reset, inject cash, view all portfolios.
Password-protected.
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime
from components.ui import section_title
from utils.data import (get_or_init_state, persist_state, load_events, save_state)


def render():
    state = get_or_init_state()

    st.markdown(
        '<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;'
        'letter-spacing:0.1em;color:#7c3aed;margin:0 0 8px;">🔐 ADMIN PANEL</h1>',
        unsafe_allow_html=True,
    )

    # ── Auth ──
    if not st.session_state.get("admin_authenticated", False):
        pw = st.text_input("Admin Password", type="password")
        if st.button("Login"):
            if pw == state.get("admin_password", "eslsca2026"):
                st.session_state["admin_authenticated"] = True
                st.rerun()
            else:
                st.error("Wrong password.")
        return

    st.success("✅ Admin authenticated")
    if st.button("Logout"):
        st.session_state["admin_authenticated"] = False
        st.rerun()

    tabs = st.tabs([
        "👥 Teams", "📰 Events", "💰 Cash Injection",
        "🔄 Reset Game", "⚙️ Settings", "📊 Full View"
    ])

    # ══════════════════════════════════════════════════════
    # TEAMS
    # ══════════════════════════════════════════════════════
    with tabs[0]:
        section_title("ALL TEAMS")
        teams = state.get("teams", {})
        for tid, team in teams.items():
            with st.expander(f"{team['emoji']} {team['name']} — ${team['cash']:,.0f} cash"):
                st.json({
                    "cash": team["cash"],
                    "holdings": team.get("holdings", {}),
                    "num_options": len(team.get("options", [])),
                    "num_trades": len(team.get("trades", [])),
                    "members": team.get("members", []),
                })

        section_title("ADD / EDIT TEAM")
        col1, col2, col3 = st.columns(3)
        with col1:
            new_tid = st.text_input("Team ID (lowercase, no spaces)")
        with col2:
            new_name = st.text_input("Team Name")
        with col3:
            new_emoji = st.text_input("Emoji", value="🐺")
        new_cash = st.number_input("Initial Cash", value=10_000_000.0, step=100_000.0)
        if st.button("➕ Add/Update Team"):
            if new_tid:
                state["teams"][new_tid] = {
                    "name": new_name or new_tid,
                    "emoji": new_emoji,
                    "cash": new_cash,
                    "holdings": {},
                    "options": [],
                    "trades": [],
                    "portfolio_history": [],
                    "members": [],
                }
                persist_state()
                st.success(f"Team '{new_tid}' saved.")
                st.rerun()

    # ══════════════════════════════════════════════════════
    # EVENTS
    # ══════════════════════════════════════════════════════
    with tabs[1]:
        section_title("MARKET EVENTS MANAGEMENT")
        events_df = load_events()
        st.dataframe(events_df, use_container_width=True, hide_index=True)

        section_title("CREATE NEW EVENT")
        col1, col2, col3 = st.columns(3)
        with col1:
            ev_headline = st.text_input("Headline")
            ev_scope = st.text_input("Scope (ticker / broad / equity / crypto…)")
        with col2:
            ev_move = st.number_input("Move (%)", value=5.0, step=0.5)
            ev_start = st.text_input("Start (YYYY-MM-DD HH:MM)", value=str(datetime.utcnow())[:16])
        with col3:
            ev_end = st.text_input("End (YYYY-MM-DD HH:MM)", value="")
            ev_active = st.checkbox("Active", value=True)

        if st.button("📣 Publish Event"):
            from pathlib import Path
            import os
            data_dir = Path(__file__).parent.parent / "data"
            ev_path = data_dir / "market_events.csv"
            new_row = pd.DataFrame([{
                "id": int(events_df["id"].max()) + 1 if not events_df.empty else 1,
                "headline": ev_headline,
                "scope": ev_scope,
                "move": f"+{ev_move:.2f}" if ev_move >= 0 else f"{ev_move:.2f}",
                "effect_type": "price_mult",
                "start_dt": ev_start,
                "end_dt": ev_end,
                "active": ev_active,
            }])
            updated = pd.concat([events_df, new_row], ignore_index=True)
            updated.to_csv(ev_path, index=False)
            st.success("Event published! It will appear in the news banner.")
            st.rerun()

    # ══════════════════════════════════════════════════════
    # CASH INJECTION
    # ══════════════════════════════════════════════════════
    with tabs[2]:
        section_title("CASH INJECTION / PENALTY")
        col1, col2, col3 = st.columns(3)
        with col1:
            inj_team = st.selectbox("Team", list(state["teams"].keys()))
        with col2:
            inj_amount = st.number_input("Amount ($)", value=0.0, step=100_000.0)
        with col3:
            inj_reason = st.text_input("Reason")

        if st.button("💸 Apply"):
            state["teams"][inj_team]["cash"] += inj_amount
            state["teams"][inj_team].setdefault("trades", []).append({
                "date": str(datetime.utcnow())[:19],
                "type": "ADMIN",
                "side": "CREDIT" if inj_amount >= 0 else "DEBIT",
                "ticker": "CASH",
                "qty": 1,
                "price": abs(inj_amount),
                "cash_impact": inj_amount,
                "note": inj_reason,
            })
            persist_state()
            st.success(f"Applied ${inj_amount:+,.0f} to {inj_team}.")
            st.rerun()

    # ══════════════════════════════════════════════════════
    # RESET
    # ══════════════════════════════════════════════════════
    with tabs[3]:
        section_title("RESET GAME")
        st.warning("⚠️ This will erase ALL trades, holdings, and history for ALL teams.")
        confirm = st.text_input("Type RESET to confirm")
        reset_cash = st.number_input("New starting cash", value=10_000_000.0, step=100_000.0)
        if st.button("🔄 RESET GAME") and confirm == "RESET":
            for tid in state["teams"]:
                state["teams"][tid]["cash"] = reset_cash
                state["teams"][tid]["holdings"] = {}
                state["teams"][tid]["options"] = []
                state["teams"][tid]["trades"] = []
                state["teams"][tid]["portfolio_history"] = []
            persist_state()
            st.success("Game reset complete.")
            st.rerun()

        section_title("RESET SINGLE TEAM")
        reset_tid = st.selectbox("Team to reset", list(state["teams"].keys()), key="reset_single")
        if st.button("Reset this team"):
            state["teams"][reset_tid]["cash"] = reset_cash
            state["teams"][reset_tid]["holdings"] = {}
            state["teams"][reset_tid]["options"] = []
            state["teams"][reset_tid]["trades"] = []
            state["teams"][reset_tid]["portfolio_history"] = []
            persist_state()
            st.success(f"Team {reset_tid} reset.")
            st.rerun()

    # ══════════════════════════════════════════════════════
    # SETTINGS
    # ══════════════════════════════════════════════════════
    with tabs[4]:
        section_title("GAME SETTINGS")
        new_pw = st.text_input("New admin password")
        if st.button("Update password") and new_pw:
            state["admin_password"] = new_pw
            persist_state()
            st.success("Password updated.")

    # ══════════════════════════════════════════════════════
    # FULL VIEW
    # ══════════════════════════════════════════════════════
    with tabs[5]:
        section_title("FULL STATE JSON")
        # Truncate trades for display
        display_state = {}
        for tid, team in state["teams"].items():
            display_state[tid] = {k: v for k, v in team.items() if k != "portfolio_history"}
            display_state[tid]["trades_count"] = len(team.get("trades", []))
        st.json(display_state)
