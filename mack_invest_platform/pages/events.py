"""
Market Events page: view active events, impact simulation.
ESLSCA Stock Market Game — v2.1
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from components.ui import section_title
from utils.data import load_events, load_assets, get_price


def render():
    st.markdown(
        '<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;'
        'letter-spacing:0.12em;color:#ff3b6b;margin:0 0 6px;'
        'text-shadow:0 0 30px rgba(255,59,107,0.5);">'
        '📰 MARKET EVENTS</h1>',
        unsafe_allow_html=True,
    )

    events_df = load_events()

    # ── Active events ──────────────────────────────────────────────────────────
    section_title("ACTIVE MARKET ALERTS", "⚡")

    if not events_df.empty and "active" in events_df.columns:
        active = events_df[events_df["active"] == True]
    else:
        active = events_df  # show all if no active column

    if not active.empty:
        for _, row in active.iterrows():
            # Safe numeric extraction — handles strings like "+0.05", "-0.12", etc.
            raw_move = str(row.get("move", "0")).replace("+", "").strip()
            try:
                move = float(raw_move)
            except ValueError:
                move = 0.0

            color  = "#00ff88" if move >= 0 else "#ff3b6b"
            border = "#00ff88" if move >= 0 else "#ff3b6b"
            bg     = "rgba(0,255,136,0.06)" if move >= 0 else "rgba(255,59,107,0.06)"
            arrow  = "▲" if move >= 0 else "▼"
            pct_display = f"{abs(move) * 100:.1f}%"

            headline = str(row.get("headline", "")).strip() or "—"
            scope    = str(row.get("scope", "")).strip()    or "—"
            start    = str(row.get("start_dt", ""))[:16]
            end      = str(row.get("end_dt",   ""))[:16]

            st.markdown(
                f'<div style="background:{bg};border-left:3px solid {border};'
                f'border-radius:6px;padding:12px 16px;margin:6px 0;">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
                f'<div>'
                f'<span style="font-family:Rajdhani,sans-serif;font-size:0.7rem;'
                f'letter-spacing:0.12em;color:#ff8c00;font-weight:700;">⚡ ALERT</span>&nbsp;&nbsp;'
                f'<b style="font-family:Exo 2,sans-serif;font-size:0.9rem;color:#e2e8f0;">{headline}</b>'
                f'</div>'
                f'<span style="font-family:Share Tech Mono,monospace;font-size:1rem;'
                f'color:{color};font-weight:bold;">{arrow} {pct_display}</span>'
                f'</div>'
                f'<div style="margin-top:6px;font-family:Share Tech Mono,monospace;font-size:0.75rem;'
                f'color:#7a93b0;">'
                f'Scope: <span style="color:#00d4ff;">{scope}</span>'
                f'&nbsp;&nbsp;|&nbsp;&nbsp;{start} → {end}'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No active market events at this time.")

    # ── All events log ─────────────────────────────────────────────────────────
    section_title("ALL EVENTS LOG", "📋")

    if not events_df.empty:
        # Format the move column as percentage string for readability
        display_df = events_df.copy()
        if "move" in display_df.columns:
            def _fmt_move(v):
                raw = str(v).replace("+", "").strip()
                try:
                    f = float(raw)
                    sign = "+" if f >= 0 else ""
                    return f"{sign}{f*100:.1f}%"
                except ValueError:
                    return str(v)
            display_df["move"] = display_df["move"].apply(_fmt_move)

        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No events data available.")

    # ── Impact simulator ───────────────────────────────────────────────────────
    section_title("PRICE IMPACT SIMULATOR", "🎯")

    st.markdown(
        '<div style="font-family:Share Tech Mono;font-size:0.78rem;color:#7a93b0;'
        'margin-bottom:12px;">'
        'Simulate the hypothetical price impact of a market shock on any listed asset.'
        '</div>',
        unsafe_allow_html=True,
    )

    assets_df = load_assets()

    if assets_df.empty or "ticker" not in assets_df.columns:
        st.warning("No assets loaded. Check your data source.")
        return

    tickers = assets_df["ticker"].tolist()

    col1, col2 = st.columns(2)

    with col1:
        sim_ticker = st.selectbox("Asset", tickers, key="sim_t")
        sim_move   = st.slider("Price shock (%)", -30.0, 30.0, -10.0, step=0.5, key="sim_shock")

    with col2:
        spot = get_price(sim_ticker)

        # Guard against NaN / None
        if spot is not None and spot == spot:  # NaN != NaN
            new_price   = spot * (1 + sim_move / 100)
            abs_change  = new_price - spot
            delta_label = f"{sim_move:+.1f}%"

            st.metric("Current Price",   f"{spot:,.4f}")
            st.metric(
                "Shocked Price",
                f"{new_price:,.4f}",
                delta=delta_label,
                delta_color="normal",
            )

            # Visual bar chart comparing before/after
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=["Current", "After Shock"],
                y=[spot, new_price],
                marker_color=["#00d4ff", "#00ff88" if sim_move >= 0 else "#ff3b6b"],
                text=[f"{spot:,.4f}", f"{new_price:,.4f}"],
                textposition="outside",
                textfont=dict(family="Share Tech Mono", size=11),
                hovertemplate="%{x}: %{y:,.4f}<extra></extra>",
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8", family="Share Tech Mono"),
                xaxis=dict(showgrid=False),
                yaxis=dict(
                    gridcolor="rgba(255,255,255,0.04)",
                    title="Price",
                ),
                margin=dict(l=10, r=10, t=30, b=10),
                height=200,
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"Price for **{sim_ticker}** is unavailable.")

    # ── Multi-asset shock table ────────────────────────────────────────────────
    section_title("MULTI-ASSET SHOCK PREVIEW", "💥")
    st.markdown(
        '<div style="font-family:Share Tech Mono;font-size:0.78rem;color:#7a93b0;'
        'margin-bottom:10px;">Apply the same shock to all assets simultaneously.</div>',
        unsafe_allow_html=True,
    )

    if st.button("▶ RUN PORTFOLIO SHOCK", key="run_shock"):
        rows = []
        for ticker in tickers:
            price = get_price(ticker)
            if price is not None and price == price:
                shocked = price * (1 + sim_move / 100)
                rows.append({
                    "Ticker":         ticker,
                    "Current Price":  f"{price:,.4f}",
                    "Shocked Price":  f"{shocked:,.4f}",
                    "Δ Abs":          f"{shocked - price:+,.4f}",
                    "Δ %":            f"{sim_move:+.1f}%",
                })
            else:
                rows.append({
                    "Ticker":        ticker,
                    "Current Price": "—",
                    "Shocked Price": "—",
                    "Δ Abs":         "—",
                    "Δ %":           "—",
                })

        if rows:
            shock_df = pd.DataFrame(rows)
            st.dataframe(shock_df, use_container_width=True, hide_index=True)
        else:
            st.info("No price data available for shock simulation.")
