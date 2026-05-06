"""
Market Events page: view active events, impact simulation.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from components.ui import section_title
from utils.data import load_events, load_assets, get_price


def render():
    st.markdown(
        '<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;'
        'letter-spacing:0.1em;color:#ff3b6b;margin:0 0 8px;">📰 MARKET EVENTS</h1>',
        unsafe_allow_html=True,
    )

    events_df = load_events()

    # ── Active events ──
    section_title("ACTIVE MARKET ALERTS")
    active = events_df[events_df["active"] == True] if "active" in events_df.columns else events_df
    if not active.empty:
        for _, row in active.iterrows():
            move = float(str(row.get("move", "0")).replace("+", ""))
            color = "#00ff88" if move >= 0 else "#ff3b6b"
            arrow = "▲" if move >= 0 else "▼"
            st.markdown(
                f'<div style="background:rgba(255,59,107,0.08);border-left:3px solid #ff3b6b;'
                f'border-radius:6px;padding:12px 16px;margin:6px 0;'
                f'font-family:Share Tech Mono,monospace;font-size:0.83rem;">'
                f'<span style="color:#ff8c00;font-weight:bold;">⚡ ALERT</span> &nbsp;'
                f'<b style="color:#e2e8f0;">{row["headline"]}</b><br>'
                f'<span style="color:#94a3b8;">Scope: <b style="color:#00d4ff;">{row["scope"]}</b> &nbsp;|&nbsp; '
                f'Move: <b style="color:{color};">{arrow} {abs(move)*100:.0f}%</b> &nbsp;|&nbsp; '
                f'{str(row.get("start_dt",""))[:16]} → {str(row.get("end_dt",""))[:16]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No active market events.")

    # ── All events table ──
    section_title("ALL EVENTS LOG")
    st.dataframe(events_df, use_container_width=True, hide_index=True)

    # ── Impact simulation ──
    section_title("PRICE IMPACT SIMULATOR")
    st.markdown(
        '<div style="font-family:Share Tech Mono;font-size:0.78rem;color:#94a3b8;">'
        'Simulate the hypothetical price impact of an event on an asset.</div>',
        unsafe_allow_html=True,
    )
    assets_df = load_assets()
    col1, col2 = st.columns(2)
    with col1:
        sim_ticker = st.selectbox("Asset", assets_df["ticker"].tolist(), key="sim_t")
        sim_move = st.slider("Price shock (%)", -30.0, 30.0, -10.0, 0.5)
    with col2:
        spot = get_price(sim_ticker)
        if spot == spot:
            new_price = spot * (1 + sim_move / 100)
            st.metric("Current Price", f"{spot:,.4f}")
            st.metric("Shocked Price", f"{new_price:,.4f}",
                      delta=f"{sim_move:+.1f}%",
                      delta_color="normal")
