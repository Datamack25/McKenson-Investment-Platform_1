"""
Market Events page: active alerts + price impact simulator with live prices.
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

    # ── Active events cards ───────────────────────────────────────────────────
    section_title("ACTIVE MARKET ALERTS")

    if not events_df.empty and "active" in events_df.columns:
        active = events_df[events_df["active"] == True]
    else:
        active = pd.DataFrame()

    if not active.empty:
        for _, row in active.iterrows():
            try:
                move = float(str(row.get("move", "0")).replace("+", "").replace("%", ""))
            except ValueError:
                move = 0.0
            color = "#00ff88" if move >= 0 else "#ff3b6b"
            arrow = "▲" if move >= 0 else "▼"
            st.markdown(
                f'<div style="background:rgba(255,59,107,0.08);border-left:3px solid #ff3b6b;'
                f'border-radius:6px;padding:12px 16px;margin:6px 0;'
                f'font-family:Share Tech Mono,monospace;font-size:0.83rem;">'
                f'<span style="color:#ff8c00;font-weight:bold;">⚡ ALERT</span>&nbsp;&nbsp;'
                f'<b style="color:#e2e8f0;">{row.get("headline","")}</b><br>'
                f'<span style="color:#94a3b8;">'
                f'Scope: <b style="color:#00d4ff;">{row.get("scope","")}</b>'
                f'&nbsp;|&nbsp;Move: <b style="color:{color};">{arrow} {abs(move)*100:.0f} bps</b>'
                f'&nbsp;|&nbsp;{str(row.get("start_dt",""))[:16]} → {str(row.get("end_dt",""))[:16]}'
                f'</span></div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No active market events.")

    # ── All events table ──────────────────────────────────────────────────────
    section_title("ALL EVENTS LOG")
    if not events_df.empty:
        st.dataframe(events_df, use_container_width=True, hide_index=True)
    else:
        st.info("No events data found. Check data/events.csv.")

    # ── Impact simulator ──────────────────────────────────────────────────────
    section_title("PRICE IMPACT SIMULATOR")
    st.markdown(
        '<div style="font-family:Share Tech Mono;font-size:0.78rem;color:#94a3b8;margin-bottom:12px;">'
        'Simulate the hypothetical price impact of a shock on any asset — prices are fetched live.</div>',
        unsafe_allow_html=True,
    )

    assets_df = load_assets()
    if assets_df.empty:
        st.warning("No assets configured.")
        return

    col1, col2 = st.columns(2)
    with col1:
        sim_ticker = st.selectbox("Select Asset", assets_df["ticker"].tolist(), key="sim_ticker")
        sim_move   = st.slider("Price Shock (%)", -50.0, 50.0, -10.0, 0.5, key="sim_move")

    with col2:
        spot = get_price(sim_ticker)

        if spot == spot:  # not NaN
            new_price  = spot * (1 + sim_move / 100)
            pnl_color  = "normal"

            st.markdown(
                f'<div style="background:rgba(0,212,255,0.06);border:1px solid rgba(0,212,255,0.2);'
                f'border-radius:8px;padding:16px;font-family:Share Tech Mono,monospace;">'
                f'<div style="color:#94a3b8;font-size:0.72rem;letter-spacing:0.1em;margin-bottom:4px;">CURRENT PRICE (LIVE)</div>'
                f'<div style="color:#e2e8f0;font-size:1.4rem;font-weight:bold;">{spot:,.4f}</div>'
                f'<div style="color:#94a3b8;font-size:0.72rem;letter-spacing:0.1em;margin:12px 0 4px;">SHOCKED PRICE</div>'
                f'<div style="color:{"#00ff88" if sim_move >= 0 else "#ff3b6b"};font-size:1.4rem;font-weight:bold;">'
                f'{new_price:,.4f} '
                f'<span style="font-size:0.9rem;">({sim_move:+.1f}%)</span>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Simple gauge chart
            fig = go.Figure(go.Indicator(
                mode="number+delta",
                value=new_price,
                delta={"reference": spot, "relative": True, "valueformat": ".2%"},
                title={"text": f"{sim_ticker} — Shocked Price", "font": {"color": "#94a3b8", "size": 13}},
                number={"font": {"color": "#00d4ff", "size": 28}},
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                height=160,
                margin=dict(t=20, b=10, l=10, r=10),
                font={"color": "#e2e8f0"},
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error(f"Could not fetch live price for {sim_ticker}. Check the ticker symbol or your connection.")
