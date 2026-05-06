"""
Dashboard: team overview, portfolio summary, quick stats.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from components.ui import section_title, metric_row
from utils.data import (get_or_init_state, load_assets, get_price,
                        value_portfolio, compute_portfolio_metrics)


def render():
    state = get_or_init_state()
    team_id = st.session_state.get("active_team", list(state["teams"].keys())[0])
    team = state["teams"][team_id]

    st.markdown(
        f'<h1 style="font-family:Rajdhani,sans-serif;font-size:2.2rem;'
        f'letter-spacing:0.1em;color:#00d4ff;margin:0 0 4px;">'
        f'{team["emoji"]} {team["name"].upper()} — PORTFOLIO DASHBOARD</h1>',
        unsafe_allow_html=True,
    )

    # ── Fetch live prices ──
    holdings = team.get("holdings", {})
    prices = {}
    for ticker in holdings:
        prices[ticker] = get_price(ticker)

    val = value_portfolio(team, prices)
    total = val["total"]
    cash = val["cash"]
    spot = val["spot_value"]
    initial = 10_000_000.0

    pnl = total - initial
    pnl_pct = pnl / initial * 100

    # ── Top metrics ──
    section_title("PORTFOLIO OVERVIEW")
    metric_row([
        {"label": "Total Value", "value": f"${total:,.0f}", "color": ""},
        {"label": "Cash", "value": f"${cash:,.0f}", "color": ""},
        {"label": "Invested", "value": f"${spot:,.0f}", "color": ""},
        {"label": "Unrealised P&L", "value": f"${pnl:+,.0f} ({pnl_pct:+.2f}%)",
         "color": "positive" if pnl >= 0 else "negative"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])

    # ── Portfolio history chart ──
    with col1:
        section_title("PORTFOLIO VALUE HISTORY")
        history = team.get("portfolio_history", [])
        if history:
            hist_df = pd.DataFrame(history)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=hist_df["date"], y=hist_df["value"],
                mode="lines", name="Portfolio",
                line=dict(color="#00d4ff", width=2),
                fill="tozeroy",
                fillcolor="rgba(0,212,255,0.05)",
            ))
            fig.add_hline(y=initial, line_dash="dot",
                          line_color="#ff3b6b", opacity=0.5,
                          annotation_text="Initial")
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8", family="Share Tech Mono"),
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                margin=dict(l=10, r=10, t=10, b=10), height=260,
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No portfolio history yet. Start trading to track value over time.")

    # ── Allocation pie ──
    with col2:
        section_title("ALLOCATION")
        if val["positions"]:
            pie_labels = [p["ticker"] for p in val["positions"]] + ["Cash"]
            pie_values = [p["market_value"] for p in val["positions"]] + [cash]
            fig2 = go.Figure(go.Pie(
                labels=pie_labels, values=pie_values,
                hole=0.55,
                marker=dict(colors=px.colors.qualitative.Dark24),
                textfont=dict(family="Share Tech Mono", size=11),
            ))
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                margin=dict(l=0, r=0, t=0, b=0), height=260,
                showlegend=True,
                legend=dict(font=dict(size=10, family="Share Tech Mono"),
                            bgcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No positions yet.")

    # ── Positions table ──
    section_title("OPEN POSITIONS")
    if val["positions"]:
        pos_df = pd.DataFrame(val["positions"])
        pos_df = pos_df.rename(columns={
            "ticker": "Ticker", "qty": "Qty",
            "avg_price": "Avg Price", "current_price": "Last Price",
            "market_value": "Mkt Value", "unreal_pnl": "Unreal. P&L", "pnl_pct": "P&L %"
        })
        for col in ["Avg Price", "Last Price", "Mkt Value"]:
            pos_df[col] = pos_df[col].apply(lambda x: f"{x:,.4f}")
        pos_df["Unreal. P&L"] = pos_df["Unreal. P&L"].apply(
            lambda x: f"+{x:,.0f}" if float(x) >= 0 else f"{float(x):,.0f}"
        )
        pos_df["P&L %"] = pos_df["P&L %"].apply(lambda x: f"{x:+.2f}%")
        st.dataframe(pos_df, use_container_width=True, hide_index=True)
    else:
        st.info("No open spot positions. Use the Trading Desk to build your portfolio.")

    # ── Risk metrics ──
    section_title("RISK METRICS (LIVE)")
    history = team.get("portfolio_history", [])
    if len(history) >= 5:
        hist_df = pd.DataFrame(history)
        rets = hist_df["value"].pct_change().dropna()
        m = compute_portfolio_metrics(rets)
        if m:
            metric_row([
                {"label": "Ann. Vol", "value": f"{m['ann_vol']*100:.2f}%", "color": ""},
                {"label": "Sharpe Ratio", "value": f"{m['sharpe']:.2f}",
                 "color": "positive" if m["sharpe"] >= 2 else "neutral"},
                {"label": "Max Drawdown", "value": f"{m['max_drawdown']*100:.2f}%",
                 "color": "negative" if m["max_drawdown"] < -0.05 else ""},
                {"label": "VaR 99% 10d", "value": f"{m['var_99_10d']*100:.2f}%", "color": ""},
                {"label": "CVaR 99% 10d", "value": f"{m['cvar_99_10d']*100:.2f}%", "color": ""},
            ])
    else:
        st.info("Risk metrics available after 5+ trading days of portfolio history.")

    # ── Recent trades ──
    section_title("RECENT TRADES")
    trades = team.get("trades", [])
    if trades:
        t_df = pd.DataFrame(trades[-20:][::-1])
        st.dataframe(t_df, use_container_width=True, hide_index=True)
    else:
        st.info("No trades yet.")
