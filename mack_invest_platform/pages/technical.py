"""
Technical Analysis: candlestick, RSI, MACD, Bollinger, GARCH forecast.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from components.ui import section_title
from utils.data import get_history, load_assets
from utils.technical import (compute_rsi, compute_macd, compute_bollinger,
                              garch_vol_forecast, signal_summary)


def render():
    st.markdown(
        '<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;'
        'letter-spacing:0.1em;color:#00d4ff;margin:0 0 8px;">📊 TECHNICAL ANALYSIS</h1>',
        unsafe_allow_html=True,
    )

    assets_df = load_assets()
    tickers = assets_df["ticker"].tolist()

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        ticker = st.selectbox("Select Asset", tickers, key="ta_ticker")
    with col2:
        period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
    with col3:
        interval = st.selectbox("Interval", ["1d", "1wk"], index=0)

    hist = get_history(ticker, period=period, interval=interval)

    if hist.empty:
        st.warning(f"No data available for {ticker}.")
        return

    closes = hist["Close"]

    # ── Signal summary ──
    section_title("SIGNAL SUMMARY")
    try:
        sig = signal_summary(closes)
        cols = st.columns(5)
        signals = [
            ("RSI", sig["RSI"], sig["RSI_signal"]),
            ("MACD Signal", sig["MACD_signal"], sig["MACD_signal"]),
            ("MACD Hist", sig["MACD_hist"], ""),
            ("Bollinger %B", sig["BB_%B"], sig["BB_signal"]),
            ("BB Signal", sig["BB_signal"], sig["BB_signal"]),
        ]
        for c, (label, val, state) in zip(cols, signals):
            color = ""
            if str(state) in ("BUY", "OVERSOLD"):
                color = "#00ff88"
            elif str(state) in ("SELL", "OVERBOUGHT"):
                color = "#ff3b6b"
            else:
                color = "#ffd700"
            with c:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-label">{label}</div>'
                    f'<div class="metric-value" style="color:{color};font-size:1.1rem;">'
                    f'{val}</div></div>',
                    unsafe_allow_html=True,
                )
    except Exception:
        pass

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Main chart ──
    tab1, tab2, tab3, tab4 = st.tabs(["🕯 Candlestick + Bollinger", "📈 RSI", "📉 MACD", "🔮 Vol Forecast"])

    with tab1:
        boll = compute_bollinger(closes)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            row_heights=[0.75, 0.25],
                            vertical_spacing=0.03)

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=hist.index, open=hist["Open"], high=hist["High"],
            low=hist["Low"], close=hist["Close"],
            name="Price",
            increasing=dict(line=dict(color="#00ff88"), fillcolor="#00ff88"),
            decreasing=dict(line=dict(color="#ff3b6b"), fillcolor="#ff3b6b"),
        ), row=1, col=1)

        # Bollinger
        fig.add_trace(go.Scatter(x=hist.index, y=boll["Upper"], name="BB Upper",
                                 line=dict(color="#7c3aed", width=1, dash="dash")), row=1, col=1)
        fig.add_trace(go.Scatter(x=hist.index, y=boll["SMA"], name="SMA 20",
                                 line=dict(color="#00d4ff", width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=hist.index, y=boll["Lower"], name="BB Lower",
                                 line=dict(color="#7c3aed", width=1, dash="dash"),
                                 fill="tonexty",
                                 fillcolor="rgba(124,58,237,0.05)"), row=1, col=1)

        # Volume
        colors = ["#00ff88" if c >= o else "#ff3b6b"
                  for c, o in zip(hist["Close"], hist["Open"])]
        fig.add_trace(go.Bar(x=hist.index, y=hist["Volume"], name="Volume",
                             marker_color=colors, opacity=0.5), row=2, col=1)

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8", family="Share Tech Mono"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.04)", rangeslider=dict(visible=False)),
            xaxis2=dict(gridcolor="rgba(255,255,255,0.04)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
            yaxis2=dict(gridcolor="rgba(255,255,255,0.04)"),
            margin=dict(l=10, r=10, t=10, b=10), height=500,
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        rsi = compute_rsi(closes)
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=rsi.index, y=rsi, name="RSI",
                                     line=dict(color="#00d4ff", width=2)))
        fig_rsi.add_hline(y=70, line_color="#ff3b6b", line_dash="dash",
                          annotation_text="Overbought 70")
        fig_rsi.add_hline(y=30, line_color="#00ff88", line_dash="dash",
                          annotation_text="Oversold 30")
        fig_rsi.add_hline(y=50, line_color="#ffd700", line_dash="dot", opacity=0.4)
        fig_rsi.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8", family="Share Tech Mono"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.04)", range=[0, 100]),
            margin=dict(l=10, r=10, t=10, b=10), height=350,
        )
        st.plotly_chart(fig_rsi, use_container_width=True)

    with tab3:
        macd_df = compute_macd(closes)
        fig_macd = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                  row_heights=[0.6, 0.4], vertical_spacing=0.05)
        fig_macd.add_trace(go.Scatter(x=macd_df.index, y=macd_df["MACD"],
                                      name="MACD", line=dict(color="#00d4ff", width=1.5)), row=1, col=1)
        fig_macd.add_trace(go.Scatter(x=macd_df.index, y=macd_df["Signal"],
                                      name="Signal", line=dict(color="#ff8c00", width=1.5)), row=1, col=1)
        hist_colors = ["#00ff88" if v >= 0 else "#ff3b6b" for v in macd_df["Histogram"]]
        fig_macd.add_trace(go.Bar(x=macd_df.index, y=macd_df["Histogram"],
                                  name="Histogram", marker_color=hist_colors), row=2, col=1)
        fig_macd.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8", family="Share Tech Mono"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
            xaxis2=dict(gridcolor="rgba(255,255,255,0.04)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
            yaxis2=dict(gridcolor="rgba(255,255,255,0.04)"),
            margin=dict(l=10, r=10, t=10, b=10), height=420,
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_macd, use_container_width=True)

    with tab4:
        section_title("GARCH-STYLE VOLATILITY FORECAST (10-DAY)")
        rets = closes.pct_change().dropna()
        try:
            forecasts = garch_vol_forecast(rets, horizon=10)
            current_vol = rets.rolling(20).std().iloc[-1] * np.sqrt(252) * 100
            fig_garch = go.Figure()
            fig_garch.add_trace(go.Scatter(
                x=list(range(1, 11)), y=[f * 100 for f in forecasts],
                mode="lines+markers",
                line=dict(color="#7c3aed", width=2),
                marker=dict(color="#00d4ff", size=7),
                name="Forecast Vol",
            ))
            fig_garch.add_hline(y=current_vol, line_color="#ffd700",
                                 line_dash="dash", annotation_text=f"Current {current_vol:.1f}%")
            fig_garch.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8", family="Share Tech Mono"),
                xaxis=dict(title="Horizon (days)", gridcolor="rgba(255,255,255,0.04)"),
                yaxis=dict(title="Ann. Vol (%)", gridcolor="rgba(255,255,255,0.04)"),
                margin=dict(l=10, r=10, t=10, b=10), height=350,
            )
            st.plotly_chart(fig_garch, use_container_width=True)
        except Exception as e:
            st.warning(f"GARCH forecast unavailable: {e}")

    # ── Return distribution ──
    section_title("RETURN DISTRIBUTION")
    rets = closes.pct_change().dropna() * 100
    fig_dist = go.Figure()
    fig_dist.add_trace(go.Histogram(
        x=rets, nbinsx=60, name="Daily Returns",
        marker_color="#00d4ff", opacity=0.7,
    ))
    q01 = rets.quantile(0.01)
    fig_dist.add_vline(x=q01, line_color="#ff3b6b", line_dash="dash",
                       annotation_text=f"VaR 99%: {q01:.2f}%")
    fig_dist.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8", family="Share Tech Mono"),
        xaxis=dict(title="Daily Return (%)", gridcolor="rgba(255,255,255,0.04)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)"),
        margin=dict(l=10, r=10, t=10, b=10), height=300,
    )
    st.plotly_chart(fig_dist, use_container_width=True)
