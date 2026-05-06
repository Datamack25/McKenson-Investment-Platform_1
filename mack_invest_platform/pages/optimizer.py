"""
Portfolio Optimizer: Markowitz + CVaR, efficient frontier, correlation heatmap.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from components.ui import section_title
from utils.data import get_multi_prices, load_assets
from utils.portfolio import (markowitz_optimise, efficient_frontier,
                              cvar_historical, annualised_vol, sharpe_ratio)


def render():
    st.markdown(
        '<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;'
        'letter-spacing:0.1em;color:#00d4ff;margin:0 0 8px;">🧮 PORTFOLIO OPTIMIZER</h1>',
        unsafe_allow_html=True,
    )

    assets_df = load_assets()
    tradeable = assets_df[assets_df["category"].isin(
        ["ETF", "Equity", "Crypto", "Commodity", "Index"]
    )]["ticker"].tolist()

    col1, col2 = st.columns([3, 1])
    with col1:
        selected = st.multiselect(
            "Select assets (min 3, max 15)",
            tradeable,
            default=["SPY", "AAPL", "MSFT", "BTC-USD", "GC=F", "^FCHI", "0700.HK"],
        )
    with col2:
        period = st.selectbox("Data period", ["6mo", "1y", "2y", "3y"], index=1)

    if len(selected) < 2:
        st.warning("Select at least 2 assets.")
        return

    with st.spinner("Fetching price history…"):
        prices_df = get_multi_prices(selected, period=period)

    if prices_df.empty or prices_df.shape[1] < 2:
        st.error("Could not fetch enough price data.")
        return

    prices_df = prices_df.dropna(axis=1, thresh=int(len(prices_df) * 0.8))
    prices_df = prices_df.dropna()
    ret_matrix = prices_df.pct_change().dropna()

    if ret_matrix.shape[0] < 30:
        st.error("Not enough history (< 30 days).")
        return

    section_title("OPTIMISATION SETTINGS")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        allow_short = st.checkbox("Allow short positions", value=False)
    with col_b:
        cvar_w = st.slider("CVaR penalty weight", 0.0, 5.0, 0.0, 0.1)
    with col_c:
        run_frontier = st.checkbox("Compute efficient frontier", value=True)

    if st.button("⚡ OPTIMISE PORTFOLIO"):
        with st.spinner("Optimising…"):
            result = markowitz_optimise(ret_matrix, allow_short=allow_short,
                                         cvar_weight=cvar_w)

        section_title("OPTIMAL WEIGHTS")
        w_df = pd.DataFrame([
            {"Asset": k, "Weight": f"{v*100:.2f}%", "Weight_num": v}
            for k, v in result["weights"].items() if abs(v) > 0.001
        ]).sort_values("Weight_num", ascending=False)

        col1, col2 = st.columns([2, 2])
        with col1:
            st.dataframe(w_df[["Asset", "Weight"]], use_container_width=True, hide_index=True)
        with col2:
            fig_pie = go.Figure(go.Pie(
                labels=w_df["Asset"], values=w_df["Weight_num"].abs(),
                hole=0.5,
                marker=dict(colors=px.colors.qualitative.Dark24),
                textfont=dict(family="Share Tech Mono", size=11),
            ))
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                margin=dict(l=0, r=0, t=0, b=0), height=280,
                legend=dict(font=dict(size=10, family="Share Tech Mono"),
                            bgcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        section_title("PORTFOLIO METRICS")
        cols = st.columns(5)
        metrics = [
            ("Expected Return (ann.)", f"{result['expected_return']*100:.2f}%"),
            ("Volatility (ann.)", f"{result['volatility']*100:.2f}%"),
            ("Sharpe Ratio", f"{result['sharpe']:.3f}"),
            ("CVaR 95%", f"{result['cvar_95']*100:.3f}%"),
            ("CVaR 99%", f"{result['cvar_99']*100:.3f}%"),
        ]
        for c, (label, val) in zip(cols, metrics):
            with c:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-label">{label}</div>'
                    f'<div class="metric-value" style="font-size:1.1rem;">{val}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        if run_frontier:
            section_title("EFFICIENT FRONTIER")
            with st.spinner("Computing frontier…"):
                ef_df = efficient_frontier(ret_matrix)
            if not ef_df.empty:
                fig_ef = go.Figure()
                fig_ef.add_trace(go.Scatter(
                    x=ef_df["vol"] * 100, y=ef_df["return"] * 100,
                    mode="lines+markers",
                    marker=dict(color=ef_df["sharpe"], colorscale="plasma",
                                size=7, showscale=True,
                                colorbar=dict(title="Sharpe", len=0.5)),
                    line=dict(color="rgba(0,212,255,0.5)", width=2),
                    name="Efficient Frontier",
                ))
                # Mark optimal
                fig_ef.add_trace(go.Scatter(
                    x=[result["volatility"] * 100],
                    y=[result["expected_return"] * 100],
                    mode="markers", name="Optimal",
                    marker=dict(color="#ffd700", size=14, symbol="star"),
                ))
                fig_ef.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#94a3b8", family="Share Tech Mono"),
                    xaxis=dict(title="Vol (% ann.)", gridcolor="rgba(255,255,255,0.04)"),
                    yaxis=dict(title="Return (% ann.)", gridcolor="rgba(255,255,255,0.04)"),
                    margin=dict(l=10, r=10, t=10, b=10), height=400,
                    legend=dict(bgcolor="rgba(0,0,0,0)"),
                )
                st.plotly_chart(fig_ef, use_container_width=True)

    # ── Correlation matrix ──
    section_title("CORRELATION MATRIX")
    corr = ret_matrix.corr()
    fig_corr = go.Figure(go.Heatmap(
        z=corr.values, x=corr.columns, y=corr.index,
        colorscale="RdBu_r", zmid=0, zmin=-1, zmax=1,
        text=corr.values.round(2),
        texttemplate="%{text}",
        textfont=dict(size=9, family="Share Tech Mono"),
    ))
    fig_corr.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8", family="Share Tech Mono"),
        margin=dict(l=10, r=10, t=10, b=10),
        height=max(350, len(selected) * 40),
    )
    st.plotly_chart(fig_corr, use_container_width=True)

    # ── Individual stats ──
    section_title("INDIVIDUAL ASSET STATS")
    stats_rows = []
    for col in ret_matrix.columns:
        s = ret_matrix[col]
        stats_rows.append({
            "Asset": col,
            "Ann. Return": f"{s.mean()*252*100:.2f}%",
            "Ann. Vol": f"{s.std()*np.sqrt(252)*100:.2f}%",
            "Sharpe": f"{(s.mean()*252)/(s.std()*np.sqrt(252)):.3f}",
            "Skew": f"{s.skew():.3f}",
            "Kurt": f"{s.kurt():.3f}",
            "CVaR 99%": f"{-s[s<=s.quantile(0.01)].mean()*100:.3f}%",
        })
    st.dataframe(pd.DataFrame(stats_rows), use_container_width=True, hide_index=True)
