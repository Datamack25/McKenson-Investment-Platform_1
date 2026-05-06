"""
Leaderboard: all teams ranked, benchmark comparison, performance breakdown.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from components.ui import section_title
from utils.data import (get_or_init_state, load_assets, get_price,
                        value_portfolio, get_history, compute_portfolio_metrics)

BENCHMARKS = {
    "S&P 500 (SPY)": "SPY",
    "Nasdaq 100 (QQQ)": "QQQ",
    "CAC 40 (^FCHI)": "^FCHI",
    "MSCI World (none)": None,
    "Gold (GC=F)": "GC=F",
    "Bitcoin (BTC-USD)": "BTC-USD",
}


def render():
    state = get_or_init_state()
    teams = state.get("teams", {})

    st.markdown(
        '<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;'
        'letter-spacing:0.1em;color:#00d4ff;margin:0 0 8px;">🏆 LEADERBOARD</h1>',
        unsafe_allow_html=True,
    )

    # ── Build leaderboard ──
    rows = []
    for tid, team in teams.items():
        holdings = team.get("holdings", {})
        prices = {t: get_price(t) for t in holdings}
        val = value_portfolio(team, prices)
        total = val["total"]
        initial = 10_000_000.0
        pnl = total - initial
        pnl_pct = pnl / initial * 100

        # Risk metrics from history
        history = team.get("portfolio_history", [])
        metrics = {}
        if len(history) >= 5:
            hist_df = pd.DataFrame(history)
            rets = hist_df["value"].pct_change().dropna()
            metrics = compute_portfolio_metrics(rets)

        rows.append({
            "Rank": 0,
            "Team": team["emoji"] + " " + team["name"],
            "team_id": tid,
            "Total Value": total,
            "Cash": val["cash"],
            "Invested": val["spot_value"],
            "P&L ($)": pnl,
            "P&L (%)": pnl_pct,
            "Sharpe": metrics.get("sharpe", 0),
            "Ann. Vol": metrics.get("ann_vol", 0) * 100,
            "Max DD": metrics.get("max_drawdown", 0) * 100,
            "# Trades": len(team.get("trades", [])),
        })

    if not rows:
        st.info("No team data yet.")
        return

    lb_df = pd.DataFrame(rows).sort_values("Total Value", ascending=False).reset_index(drop=True)
    lb_df["Rank"] = lb_df.index + 1

    # ── Podium ──
    section_title("PODIUM")
    top3 = lb_df.head(3)
    podium_cols = st.columns(3)
    medals = ["🥇", "🥈", "🥉"]
    for i, (col, (_, row)) in enumerate(zip(podium_cols, top3.iterrows())):
        with col:
            color = ["#ffd700", "#c0c0c0", "#cd7f32"][i]
            st.markdown(
                f'<div style="text-align:center;background:linear-gradient(135deg,rgba({",".join(str(int(int(color[1:3],16))) for _ in [0])},0,0,0.3) 0%,#111827 100%);'
                f'border:2px solid {color};border-radius:12px;padding:20px;box-shadow:0 0 30px rgba(255,215,0,{0.4-i*0.1});">'
                f'<div style="font-size:2.5rem">{medals[i]}</div>'
                f'<div style="font-family:Rajdhani;font-size:1.3rem;font-weight:700;color:{color}">{row["Team"]}</div>'
                f'<div style="font-family:Share Tech Mono;font-size:1.1rem;color:#e2e8f0">${row["Total Value"]:,.0f}</div>'
                f'<div style="font-family:Share Tech Mono;font-size:0.85rem;color:{"#00ff88" if row["P&L (%)"]>=0 else "#ff3b6b"}">{row["P&L (%)"]:.2f}%</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Full table ──
    section_title("FULL RANKINGS")
    display_df = lb_df[[
        "Rank", "Team", "Total Value", "P&L ($)", "P&L (%)",
        "Sharpe", "Ann. Vol", "Max DD", "# Trades"
    ]].copy()
    display_df["Total Value"] = display_df["Total Value"].apply(lambda x: f"${x:,.0f}")
    display_df["P&L ($)"] = display_df["P&L ($)"].apply(lambda x: f"${x:+,.0f}")
    display_df["P&L (%)"] = display_df["P&L (%)"].apply(lambda x: f"{x:+.2f}%")
    display_df["Sharpe"] = display_df["Sharpe"].apply(lambda x: f"{x:.3f}")
    display_df["Ann. Vol"] = display_df["Ann. Vol"].apply(lambda x: f"{x:.2f}%")
    display_df["Max DD"] = display_df["Max DD"].apply(lambda x: f"{x:.2f}%")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ── Portfolio value comparison chart ──
    section_title("PORTFOLIO VALUE COMPARISON")
    fig_compare = go.Figure()
    colors_team = px.colors.qualitative.Dark24
    for i, (_, row) in enumerate(lb_df.iterrows()):
        tid = row["team_id"]
        hist = teams[tid].get("portfolio_history", [])
        if hist:
            h_df = pd.DataFrame(hist)
            fig_compare.add_trace(go.Scatter(
                x=h_df["date"], y=h_df["value"],
                mode="lines", name=row["Team"],
                line=dict(color=colors_team[i % len(colors_team)], width=2),
            ))
    if fig_compare.data:
        fig_compare.add_hline(y=10_000_000, line_dash="dot",
                               line_color="#475569", annotation_text="Initial $10M")
        fig_compare.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8", family="Share Tech Mono"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
            margin=dict(l=10, r=10, t=10, b=10), height=380,
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        )
        st.plotly_chart(fig_compare, use_container_width=True)
    else:
        st.info("Portfolio history will appear here once teams start trading.")

    # ── Benchmark comparison ──
    st.markdown("<br>", unsafe_allow_html=True)
    section_title("BENCHMARK COMPARISON")

    selected_team_label = st.selectbox(
        "Compare team vs benchmark",
        lb_df["Team"].tolist(),
    )
    bench_label = st.selectbox("Benchmark", list(BENCHMARKS.keys()))
    bench_ticker = BENCHMARKS[bench_label]

    selected_tid = lb_df[lb_df["Team"] == selected_team_label]["team_id"].iloc[0]
    team_hist = teams[selected_tid].get("portfolio_history", [])

    if bench_ticker and team_hist:
        bench_hist = get_history(bench_ticker, period="6mo")
        if not bench_hist.empty:
            fig_bench = go.Figure()

            # Team normalised
            th_df = pd.DataFrame(team_hist)
            if not th_df.empty:
                t_norm = th_df["value"] / th_df["value"].iloc[0] * 100
                fig_bench.add_trace(go.Scatter(
                    x=th_df["date"], y=t_norm,
                    name=selected_team_label,
                    line=dict(color="#00d4ff", width=2),
                ))

            # Benchmark normalised
            bench_close = bench_hist["Close"]
            bench_norm = bench_close / bench_close.iloc[0] * 100
            fig_bench.add_trace(go.Scatter(
                x=bench_hist.index, y=bench_norm,
                name=bench_label,
                line=dict(color="#ffd700", width=2, dash="dash"),
            ))

            fig_bench.add_hline(y=100, line_dash="dot", line_color="#475569")
            fig_bench.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8", family="Share Tech Mono"),
                xaxis=dict(title="Date", gridcolor="rgba(255,255,255,0.04)"),
                yaxis=dict(title="Normalised (base 100)", gridcolor="rgba(255,255,255,0.04)"),
                margin=dict(l=10, r=10, t=10, b=10), height=400,
                legend=dict(bgcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig_bench, use_container_width=True)
        else:
            st.info(f"Could not fetch benchmark data for {bench_ticker}.")
    elif not bench_ticker:
        st.info("MSCI World not available via yfinance. Select another benchmark.")
    else:
        st.info("No portfolio history to compare yet.")

    # ── Sharpe / Risk scatter ──
    section_title("RISK-RETURN MAP")
    risk_rows = lb_df[lb_df["Ann. Vol"] != "0.00%"].copy()
    if not risk_rows.empty:
        risk_rows["Ann. Vol_f"] = risk_rows["Ann. Vol"].str.replace("%", "").astype(float)
        risk_rows["P&L_f"] = risk_rows["P&L (%)"].str.replace("%", "").replace("+", "").astype(float)
        fig_scatter = go.Figure()
        fig_scatter.add_trace(go.Scatter(
            x=risk_rows["Ann. Vol_f"], y=risk_rows["P&L_f"],
            mode="markers+text",
            text=risk_rows["Team"],
            textposition="top center",
            marker=dict(size=14, color=colors_team[:len(risk_rows)]),
        ))
        fig_scatter.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8", family="Share Tech Mono"),
            xaxis=dict(title="Annualised Vol (%)", gridcolor="rgba(255,255,255,0.04)"),
            yaxis=dict(title="Total Return (%)", gridcolor="rgba(255,255,255,0.04)"),
            margin=dict(l=10, r=10, t=10, b=10), height=350,
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
