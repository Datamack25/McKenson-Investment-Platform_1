"""
Dashboard: team overview, portfolio summary, quick stats + live market snapshot.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from components.ui import section_title, metric_row
from utils.data import (
    get_or_init_state,
    load_assets,
    get_price,
)


def render():
    st.markdown(
        '<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;'
        'letter-spacing:0.1em;color:#00d4ff;margin:0 0 8px;">🏠 DASHBOARD</h1>',
        unsafe_allow_html=True,
    )

    # ── State & team guard ────────────────────────────────────────────────────
    state = get_or_init_state()
    teams = state.get("teams", {})

    if not teams:
        st.warning("⚠️ No teams found. Please add teams via the Admin Panel or check data/teams.csv.")
        return

    active_team_id = st.session_state.get("active_team")
    if not active_team_id or active_team_id not in teams:
        active_team_id = list(teams.keys())[0]
        st.session_state["active_team"] = active_team_id

    team = teams[active_team_id]

    # ── Team header ───────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="background:rgba(0,212,255,0.07);border:1px solid rgba(0,212,255,0.2);'
        f'border-radius:10px;padding:14px 20px;margin-bottom:16px;'
        f'font-family:Rajdhani,sans-serif;">'
        f'<span style="font-size:1.8rem;">{team.get("emoji","🏦")}</span>&nbsp;&nbsp;'
        f'<span style="font-size:1.4rem;font-weight:700;color:#e2e8f0;">{team.get("name","—")}</span>'
        f'&nbsp;&nbsp;<span style="font-size:0.8rem;color:#94a3b8;letter-spacing:0.1em;">ACTIVE TEAM</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Portfolio summary ─────────────────────────────────────────────────────
    section_title("PORTFOLIO SUMMARY")
    portfolio = team.get("portfolio", {})
    cash = float(team.get("cash", 0))

    assets_df = load_assets()
    ticker_list = assets_df["ticker"].tolist() if not assets_df.empty else []

    # Compute market value of holdings
    total_market_value = 0.0
    holdings_rows = []
    for ticker, qty in portfolio.items():
        if qty <= 0:
            continue
        price = get_price(ticker)
        value = price * qty if price == price else 0.0
        total_market_value += value
        holdings_rows.append({
            "Ticker": ticker,
            "Qty": qty,
            "Price (live)": f"{price:,.4f}" if price == price else "—",
            "Value": f"{value:,.2f}",
        })

    total_assets = cash + total_market_value
    initial_cash = float(state.get("settings", {}).get("initial_cash", 100_000))
    pnl = total_assets - initial_cash
    pnl_pct = (pnl / initial_cash * 100) if initial_cash else 0

    pnl_color = "positive" if pnl >= 0 else "negative"
    metric_row([
        {"label": "Cash Available",    "value": f"${cash:,.2f}",             "color": "neutral"},
        {"label": "Holdings Value",    "value": f"${total_market_value:,.2f}", "color": ""},
        {"label": "Total Assets",      "value": f"${total_assets:,.2f}",      "color": ""},
        {"label": "P&L",               "value": f"{pnl:+,.2f} ({pnl_pct:+.1f}%)", "color": pnl_color},
    ])

    # ── Holdings table ────────────────────────────────────────────────────────
    if holdings_rows:
        section_title("CURRENT HOLDINGS")
        st.dataframe(
            pd.DataFrame(holdings_rows),
            use_container_width=True,
            hide_index=True,
        )

        # Mini pie chart
        fig = px.pie(
            pd.DataFrame(holdings_rows),
            names="Ticker",
            values=[float(r["Value"].replace(",", "")) for r in holdings_rows],
            color_discrete_sequence=px.colors.sequential.ice,
            hole=0.45,
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#e2e8f0",
            margin=dict(t=10, b=10, l=10, r=10),
            height=280,
            showlegend=True,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No holdings yet. Go to the Trading Desk to buy assets.")

    # ── Live market snapshot ──────────────────────────────────────────────────
    section_title("LIVE MARKET SNAPSHOT")
    st.markdown(
        '<div style="font-family:Share Tech Mono;font-size:0.75rem;color:#94a3b8;margin-bottom:8px;">'
        'Prices fetched live from Yahoo Finance — refreshed every 60 s.</div>',
        unsafe_allow_html=True,
    )

    if ticker_list:
        cols = st.columns(min(len(ticker_list), 5))
        for i, ticker in enumerate(ticker_list):
            price = get_price(ticker)
            col = cols[i % len(cols)]
            with col:
                if price == price:  # NaN check
                    st.metric(label=ticker, value=f"{price:,.2f}")
                else:
                    st.metric(label=ticker, value="—")
    else:
        st.info("No assets configured. Check data/assets.csv.")

    # ── All teams leaderboard snapshot ────────────────────────────────────────
    section_title("TEAMS OVERVIEW")
    rows = []
    for tid, t in teams.items():
        t_cash = float(t.get("cash", 0))
        t_port = t.get("portfolio", {})
        t_mv = 0.0
        for tk, qty in t_port.items():
            p = get_price(tk)
            if p == p:
                t_mv += p * qty
        rows.append({
            "Team": t.get("emoji", "") + " " + t.get("name", tid),
            "Cash": f"${t_cash:,.0f}",
            "Holdings": f"${t_mv:,.0f}",
            "Total": f"${t_cash + t_mv:,.0f}",
        })

    if rows:
        df_teams = pd.DataFrame(rows)
        st.dataframe(df_teams, use_container_width=True, hide_index=True)
