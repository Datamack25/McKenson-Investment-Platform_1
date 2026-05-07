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

    # ── CSS animation pour les bandeaux défilants ──
    st.markdown("""
    <style>
    @keyframes marquee {
        0%   { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }
    .ticker-container {
        background: rgba(0, 0, 0, 0.35);
        overflow: hidden;
        white-space: nowrap;
        padding: 9px 0;
        border-top: 1px solid #ff3b6b;
        border-bottom: 1px solid #ff3b6b;
        margin-bottom: 18px;
    }
    .ticker-container.prices {
        border-color: #00d4ff;
    }
    .ticker-wrapper {
        display: inline-block;
        animation: marquee 35s linear infinite;
    }
    .ticker-item {
        display: inline-block;
        padding: 0 28px;
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.82rem;
    }
    .ticker-sep {
        color: #475569;
        padding: 0 6px;
    }
    </style>
    """, unsafe_allow_html=True)

    events_df = load_events()
    assets_df = load_assets()

    # ── BANDEAU 1 : PRIX DES ACTIFS (défilant) ──
    st.markdown(
        '<div style="font-family:Rajdhani,sans-serif;font-size:0.75rem;'
        'letter-spacing:0.12em;color:#00d4ff;margin-bottom:4px;">⚙ LIVE ASSET PRICES</div>',
        unsafe_allow_html=True,
    )
    price_items = ""
    for _, asset in assets_df.iterrows():
        ticker = asset["ticker"]
        price = get_price(ticker)
        if price == price:  # not NaN
            price_items += (
                f'<span class="ticker-item">'
                f'<span style="color:#94a3b8;">{ticker}</span> '
                f'<b style="color:#ffffff;">{price:,.4f}</b>'
                f'</span>'
                f'<span class="ticker-sep">|</span>'
            )
        else:
            price_items += (
                f'<span class="ticker-item">'
                f'<span style="color:#94a3b8;">{ticker}</span> '
                f'<b style="color:#475569;">N/A</b>'
                f'</span>'
                f'<span class="ticker-sep">|</span>'
            )
    # Doubler le contenu pour un défilement infini sans blanc
    price_html = (
        f'<div class="ticker-container prices">'
        f'<div class="ticker-wrapper">{price_items}{price_items}</div>'
        f'</div>'
    )
    st.markdown(price_html, unsafe_allow_html=True)

    # ── BANDEAU 2 : NEWS / ALERTES ACTIVES (défilant) ──
    active = events_df[events_df["active"] == True] if "active" in events_df.columns else events_df

    st.markdown(
        '<div style="font-family:Rajdhani,sans-serif;font-size:0.75rem;'
        'letter-spacing:0.12em;color:#ff8c00;margin-bottom:4px;">⚡ LIVE NEWS FEED</div>',
        unsafe_allow_html=True,
    )
    if not active.empty:
        news_items = ""
        for _, row in active.iterrows():
            move = float(str(row.get("move", "0")).replace("+", ""))
            color = "#00ff88" if move >= 0 else "#ff3b6b"
            arrow = "▲" if move >= 0 else "▼"
            news_items += (
                f'<span class="ticker-item">'
                f'<span style="color:#ff8c00;font-weight:bold;">⚡ ALERT</span> '
                f'<span style="color:#e2e8f0;">{row["headline"]}</span> '
                f'<span style="color:#94a3b8;">({row["scope"]})</span> '
                f'<span style="color:{color};">{arrow} {abs(move)*100:.1f}%</span>'
                f'</span>'
                f'<span class="ticker-sep">◆</span>'
            )
        news_html = (
            f'<div class="ticker-container" style="border-color:#ff8c00;">'
            f'<div class="ticker-wrapper" style="animation-duration:40s;">'
            f'{news_items}{news_items}'
            f'</div></div>'
        )
        st.markdown(news_html, unsafe_allow_html=True)
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

    col1, col2 = st.columns(2)
    with col1:
        sim_ticker = st.selectbox("Asset", assets_df["ticker"].tolist(), key="sim_t")
        sim_move = st.slider("Price shock (%)", -30.0, 30.0, -10.0, 0.5)
    with col2:
        spot = get_price(sim_ticker)
        if spot == spot:
            new_price = spot * (1 + sim_move / 100)
            st.metric("Current Price", f"{spot:,.4f}")
            st.metric(
                "Shocked Price",
                f"{new_price:,.4f}",
                delta=f"{sim_move:+.1f}%",
                delta_color="normal",
            )
        else:
            st.warning("Could not fetch live price for this asset.")
