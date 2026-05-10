# pages/optimizer.py  —  MAM Portfolio Optimizer
"""
Markowitz Mean-Variance, CVaR minimization, Efficient Frontier,
correlation heatmap, portfolio rebalancing suggestions.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from components.ui import section_title, metric_row
from utils.data import get_history, load_assets, get_multi_prices
from utils.portfolio import (
    compute_stats, markowitz_optimize, cvar_optimize, efficient_frontier,
)

_P = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
          font=dict(color="#94a3b8", family="Share Tech Mono"),
          margin=dict(l=8, r=8, t=32, b=8))


def render():
    st.markdown(
        '<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;letter-spacing:.12em;'
        'color:#00d4ff;margin:0 0 2px;text-shadow:0 0 30px rgba(0,212,255,.4);">'
        '🧮 PORTFOLIO OPTIMIZER — MAM</h1>', unsafe_allow_html=True)

    st.markdown("""
    <div style="background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.2);
    border-radius:8px;padding:12px 16px;margin-bottom:16px;font-family:Share Tech Mono;
    font-size:.74rem;color:#94a3b8;line-height:1.8;">
    🧮 <b style="color:#00d4ff;">Optimisation de portefeuille</b> — Théorie Moderne du Portefeuille (Markowitz 1952) +
    CVaR (Expected Shortfall) + Frontière Efficiente.<br>
    Sélectionnez 2 à 15 actifs, définissez vos paramètres, et obtenez l'allocation optimale.
    </div>""", unsafe_allow_html=True)

    tab_build, tab_frontier, tab_heatmap, tab_compare = st.tabs([
        "⚙️ CONSTRUIRE UN PORTEFEUILLE",
        "📈 FRONTIÈRE EFFICIENTE",
        "🔥 CORRÉLATIONS",
        "📊 COMPARAISON STRATÉGIES",
    ])

    with tab_build:
        _build_tab()
    with tab_frontier:
        _frontier_tab()
    with tab_heatmap:
        _heatmap_tab()
    with tab_compare:
        _compare_tab()


# ─────────────────────────────────────────────────────────────────────────────
def _build_tab():
    section_title("SÉLECTION DES ACTIFS", "⚙️")

    assets_df = load_assets()
    col1, col2 = st.columns([2, 1])
    with col1:
        cats = st.multiselect("Catégories", sorted(assets_df["category"].unique()),
                               default=["Equities", "ETF"], key="opt_cats")
    with col2:
        period = st.selectbox("Historique", ["6mo", "1y", "2y", "3y"], index=1, key="opt_period")

    df_f = assets_df[assets_df["category"].isin(cats)] if cats else assets_df
    ticker_opts = [f'{r["ticker"]} — {r["name"]}' for _, r in df_f.iterrows()]

    defaults = []
    default_tickers = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "SPY", "GLD", "BTC-USD"]
    for t in default_tickers:
        match = [opt for opt in ticker_opts if opt.startswith(t + " ")]
        if match:
            defaults.append(match[0])

    selected = st.multiselect("Actifs (2–15)", ticker_opts, default=defaults[:6], key="opt_assets")
    tickers  = [s.split(" — ")[0] for s in selected]

    if len(tickers) < 2:
        st.warning("Sélectionnez au moins 2 actifs.")
        return

    col_r, col_m = st.columns([1, 1])
    with col_r:
        rf = st.slider("Taux sans risque (%)", 0.0, 8.0, 4.25, 0.05, key="opt_rf") / 100
    with col_m:
        method = st.radio("Objectif d'optimisation", ["Max Sharpe", "Min Volatilité", "Min CVaR"],
                           horizontal=True, key="opt_method")

    with st.spinner("⏳ Téléchargement des données historiques..."):
        price_data = {}
        for t in tickers:
            h = get_history(t, period)
            if not h.empty and "Close" in h.columns:
                price_data[t] = h["Close"]

    if len(price_data) < 2:
        st.error("Impossible de charger les données pour les actifs sélectionnés.")
        return

    prices_df = pd.DataFrame(price_data).dropna()
    if len(prices_df) < 30:
        st.warning("Historique trop court (< 30 points). Essayez une période plus longue.")
        return

    mu, cov = compute_stats(prices_df)
    daily   = prices_df.pct_change().dropna()

    with st.spinner("🧮 Optimisation en cours..."):
        if method == "Max Sharpe":
            result = markowitz_optimize(mu, cov, rf=rf, objective="sharpe")
        elif method == "Min Volatilité":
            result = markowitz_optimize(mu, cov, rf=rf, objective="min_vol")
        else:
            result = cvar_optimize(daily, alpha=0.05)

    if not result:
        st.error("Optimisation échouée. Essayez avec d'autres actifs ou une période plus longue.")
        return

    # ── Results ────────────────────────────────────────────────────────────────
    section_title("ALLOCATION OPTIMALE", "🏆")
    weights = result["weights"]

    metric_row([
        {"label": "Rendement attendu", "value": f'{result["return"]*100:+.2f}%',
         "color": "positive" if result["return"] >= 0 else "negative"},
        {"label": "Volatilité",        "value": f'{result["volatility"]*100:.2f}%', "color": ""},
        {"label": "Sharpe Ratio",      "value": f'{result["sharpe"]:.3f}',
         "color": "positive" if result["sharpe"] >= 1 else "neutral" if result["sharpe"] >= 0 else "negative"},
        {"label": "Taux sans risque",  "value": f"{rf*100:.2f}%", "color": ""},
    ])

    col_pie, col_bar = st.columns([1, 1])
    significant = {k: v for k, v in weights.items() if v > 0.005}

    with col_pie:
        fig_pie = go.Figure(go.Pie(
            labels=list(significant.keys()),
            values=list(significant.values()),
            hole=0.55,
            marker=dict(colors=px.colors.qualitative.Dark24),
            textfont=dict(family="Share Tech Mono", size=10),
            hovertemplate="<b>%{label}</b><br>%{percent}<extra></extra>"))
        fig_pie.update_layout(**_P, height=300, showlegend=True,
            title=dict(text="Allocation", font=dict(color="#00d4ff", size=13), x=0.01),
            legend=dict(font=dict(size=9, family="Share Tech Mono"), bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_bar:
        sorted_w = sorted(significant.items(), key=lambda x: x[1], reverse=True)
        fig_bar = go.Figure(go.Bar(
            x=[f'{w*100:.1f}%' for _, w in sorted_w],
            y=[t for t, _ in sorted_w],
            orientation="h",
            marker_color=[f"rgba(0,212,255,{0.4 + w*0.6})" for _, w in sorted_w],
            text=[f'{w*100:.1f}%' for _, w in sorted_w],
            textposition="outside",
            hovertemplate="%{y}: %{x}<extra></extra>"))
        fig_bar.update_layout(**_P, height=300,
            title=dict(text="Poids (%)", font=dict(color="#00d4ff", size=13), x=0.01),
            xaxis=dict(showgrid=False),
            yaxis=dict(autorange="reversed", gridcolor="rgba(255,255,255,.04)"))
        st.plotly_chart(fig_bar, use_container_width=True)

    # Weight table
    section_title("DÉTAIL DES POIDS", "📋")
    prices_raw = get_multi_prices(tuple(tickers))
    rows_w = []
    for t, w in sorted(weights.items(), key=lambda x: x[1], reverse=True):
        if w > 0.001:
            price, pct = prices_raw.get(t, (0, 0))
            rows_w.append({
                "Ticker": t,
                "Poids (%)": f"{w*100:.2f}%",
                "Allocation ($1M)": f"${w*1_000_000:,.0f}",
                "Prix actuel": f"${price:,.4f}",
                "Variation": f'{"▲" if pct>=0 else "▼"} {abs(pct):.2f}%',
            })
    if rows_w:
        st.dataframe(pd.DataFrame(rows_w), use_container_width=True, hide_index=True)

    # Cumulative performance
    section_title("PERFORMANCE SIMULÉE (historique)", "📈")
    opt_weights_arr = np.array([weights.get(t, 0) for t in prices_df.columns])
    port_returns    = (daily * opt_weights_arr).sum(axis=1)
    cumul           = (1 + port_returns).cumprod()
    equal_w         = (daily * (1/len(prices_df.columns))).sum(axis=1)
    cumul_eq        = (1 + equal_w).cumprod()

    fig_perf = go.Figure()
    fig_perf.add_trace(go.Scatter(x=cumul.index, y=(cumul - 1) * 100,
        name="Portefeuille optimisé", line=dict(color="#00d4ff", width=2.5),
        fill="tozeroy", fillcolor="rgba(0,212,255,.06)",
        hovertemplate="%{x|%d %b}<br>Perf: %{y:.2f}%<extra></extra>"))
    fig_perf.add_trace(go.Scatter(x=cumul_eq.index, y=(cumul_eq - 1) * 100,
        name="Equal Weight",
        line=dict(color="#7a93b0", width=1.5, dash="dot"),
        hovertemplate="%{x|%d %b}<br>EW: %{y:.2f}%<extra></extra>"))
    fig_perf.add_hline(y=0, line_color="rgba(255,255,255,.2)")
    fig_perf.update_layout(**_P, height=280,
        legend=dict(orientation="h", y=1.02, font=dict(size=10)),
        xaxis=dict(gridcolor="rgba(255,255,255,.04)"),
        yaxis=dict(title="Performance cumulée (%)", gridcolor="rgba(255,255,255,.04)"))
    st.plotly_chart(fig_perf, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
def _frontier_tab():
    section_title("FRONTIÈRE EFFICIENTE DE MARKOWITZ", "📈")

    assets_df = load_assets()
    eq_assets = assets_df[assets_df["category"].isin(["Equities", "ETF", "Crypto"])]
    ticker_opts = [f'{r["ticker"]} — {r["name"]}' for _, r in eq_assets.iterrows()]

    defaults = ["AAPL — Apple Inc.", "MSFT — Microsoft Corp.", "NVDA — NVIDIA Corp.",
                "AMZN — Amazon.com Inc.", "GOOGL — Alphabet Inc.", "GLD — SPDR Gold Shares"]
    defaults = [d for d in defaults if d in ticker_opts]

    col1, col2 = st.columns([3, 1])
    with col1:
        selected = st.multiselect("Actifs pour la frontière", ticker_opts,
                                   default=defaults, key="front_assets",
                                   max_selections=12)
    with col2:
        period = st.selectbox("Période", ["1y", "2y", "3y"], index=1, key="front_period")

    tickers = [s.split(" — ")[0] for s in selected]
    if len(tickers) < 3:
        st.warning("Sélectionnez au moins 3 actifs.")
        return

    with st.spinner("⏳ Calcul de la frontière..."):
        price_data = {}
        for t in tickers:
            h = get_history(t, period)
            if not h.empty and "Close" in h.columns:
                price_data[t] = h["Close"]

    if len(price_data) < 3:
        st.error("Données insuffisantes.")
        return

    prices_df = pd.DataFrame(price_data).dropna()
    mu, cov   = compute_stats(prices_df)
    rf        = 0.0425

    frontier_df = efficient_frontier(mu, cov, n_points=60)
    best_sharpe = markowitz_optimize(mu, cov, rf=rf, objective="sharpe")
    min_vol     = markowitz_optimize(mu, cov, rf=rf, objective="min_vol")

    fig = go.Figure()

    # Scatter of random portfolios
    fig.add_trace(go.Scatter(
        x=frontier_df["volatility"] * 100,
        y=frontier_df["return"] * 100,
        mode="markers",
        marker=dict(
            size=4,
            color=frontier_df["sharpe"],
            colorscale="Viridis",
            showscale=True,
            colorbar=dict(title="Sharpe", tickfont=dict(size=9, family="Share Tech Mono")),
            opacity=0.5,
        ),
        name="Portefeuilles",
        hovertemplate="Vol: %{x:.1f}%<br>Ret: %{y:.1f}%<br>Sharpe: %{marker.color:.2f}<extra></extra>"))

    # Max Sharpe point
    if best_sharpe:
        fig.add_trace(go.Scatter(
            x=[best_sharpe["volatility"] * 100],
            y=[best_sharpe["return"] * 100],
            mode="markers+text",
            marker=dict(size=15, color="#ffd700", symbol="star"),
            text=["⭐ Max Sharpe"], textposition="top right",
            textfont=dict(color="#ffd700", size=10, family="Rajdhani"),
            name=f'Max Sharpe ({best_sharpe["sharpe"]:.2f})',
            hovertemplate=f'Max Sharpe: {best_sharpe["sharpe"]:.3f}<br>Vol: {best_sharpe["volatility"]*100:.1f}%<br>Ret: {best_sharpe["return"]*100:.1f}%<extra></extra>'))

    # Min Vol point
    if min_vol:
        fig.add_trace(go.Scatter(
            x=[min_vol["volatility"] * 100],
            y=[min_vol["return"] * 100],
            mode="markers+text",
            marker=dict(size=12, color="#00ff88", symbol="diamond"),
            text=["🛡 Min Vol"], textposition="top right",
            textfont=dict(color="#00ff88", size=10, family="Rajdhani"),
            name=f'Min Vol ({min_vol["volatility"]*100:.1f}%)',
            hovertemplate=f'Min Volatilité<br>Vol: {min_vol["volatility"]*100:.1f}%<br>Ret: {min_vol["return"]*100:.1f}%<extra></extra>'))

    # Capital Market Line
    if best_sharpe:
        x_cml = np.linspace(0, best_sharpe["volatility"] * 100 * 1.5, 100)
        y_cml = rf * 100 + (best_sharpe["sharpe"]) * x_cml
        fig.add_trace(go.Scatter(x=x_cml, y=y_cml, name="Capital Market Line",
            line=dict(color="rgba(255,215,0,.4)", width=1.5, dash="dot"),
            hovertemplate="CML: %{x:.1f}% vol → %{y:.1f}% ret<extra></extra>"))

    # Individual assets
    prices_raw = get_multi_prices(tuple(tickers))
    for t in tickers:
        if t in mu.index:
            t_vol = np.sqrt(float(cov.loc[t, t])) * 100
            t_ret = float(mu[t]) * 100
            fig.add_trace(go.Scatter(
                x=[t_vol], y=[t_ret],
                mode="markers+text",
                marker=dict(size=8, color="#ff3b6b", symbol="x"),
                text=[t], textposition="top center",
                textfont=dict(color="#7a93b0", size=9, family="Share Tech Mono"),
                name=t, showlegend=False,
                hovertemplate=f"{t}<br>Vol: {t_vol:.1f}%<br>Ret: {t_ret:.1f}%<extra></extra>"))

    fig.update_layout(**_P, height=520,
        title=dict(text="Frontière Efficiente de Markowitz", font=dict(color="#00d4ff", size=14), x=0.01),
        legend=dict(orientation="h", y=1.05, font=dict(size=10)),
        xaxis=dict(title="Volatilité annualisée (%)", gridcolor="rgba(255,255,255,.04)"),
        yaxis=dict(title="Rendement annualisé (%)", gridcolor="rgba(255,255,255,.04)"))
    st.plotly_chart(fig, use_container_width=True)

    if best_sharpe and min_vol:
        metric_row([
            {"label": "Max Sharpe — Rendement", "value": f'{best_sharpe["return"]*100:.2f}%', "color": "positive"},
            {"label": "Max Sharpe — Volatilité", "value": f'{best_sharpe["volatility"]*100:.2f}%', "color": ""},
            {"label": "Max Sharpe — Ratio",      "value": f'{best_sharpe["sharpe"]:.3f}', "color": "positive"},
            {"label": "Min Vol — Volatilité",    "value": f'{min_vol["volatility"]*100:.2f}%', "color": ""},
        ])


# ─────────────────────────────────────────────────────────────────────────────
def _heatmap_tab():
    section_title("MATRICE DE CORRÉLATION", "🔥")

    assets_df = load_assets()
    ticker_opts = [f'{r["ticker"]} — {r["name"]}' for _, r in assets_df.iterrows()]
    defaults = ["AAPL — Apple Inc.", "MSFT — Microsoft Corp.", "NVDA — NVIDIA Corp.",
                "AMZN — Amazon.com Inc.", "GOOGL — Alphabet Inc.", "META — Meta Platforms",
                "SPY — SPDR S&P 500 ETF", "GLD — SPDR Gold Shares",
                "BTC-USD — Bitcoin", "GC=F — Gold Futures"]
    defaults = [d for d in defaults if d in ticker_opts]

    col1, col2 = st.columns([3, 1])
    with col1:
        selected = st.multiselect("Actifs pour la heatmap", ticker_opts,
                                   default=defaults, key="heat_assets",
                                   max_selections=20)
    with col2:
        period = st.selectbox("Période", ["3mo", "6mo", "1y", "2y"], index=2, key="heat_period")

    tickers = [s.split(" — ")[0] for s in selected]
    if len(tickers) < 2:
        st.warning("Sélectionnez au moins 2 actifs.")
        return

    with st.spinner("⏳ Calcul des corrélations..."):
        price_data = {}
        for t in tickers:
            h = get_history(t, period)
            if not h.empty and "Close" in h.columns:
                price_data[t] = h["Close"]

    if len(price_data) < 2:
        st.error("Données insuffisantes.")
        return

    prices_df = pd.DataFrame(price_data).dropna()
    daily     = prices_df.pct_change().dropna()
    corr      = daily.corr()

    # Heatmap
    fig = go.Figure(go.Heatmap(
        z=corr.values,
        x=corr.columns.tolist(),
        y=corr.index.tolist(),
        colorscale=[
            [0.0, "rgba(255,59,107,0.9)"],
            [0.5, "rgba(13,22,40,0.8)"],
            [1.0, "rgba(0,212,255,0.9)"],
        ],
        zmin=-1, zmax=1,
        text=corr.round(2).values,
        texttemplate="%{text}",
        textfont=dict(size=10, family="Share Tech Mono"),
        colorbar=dict(
            title="Corr.",
            tickfont=dict(size=9, family="Share Tech Mono"),
            tickvals=[-1, -0.5, 0, 0.5, 1],
        ),
        hovertemplate="%{x} × %{y}<br>Corrélation: %{z:.3f}<extra></extra>"))

    n = len(tickers)
    fig.update_layout(**_P, height=max(350, n * 38),
        title=dict(text="Corrélations des rendements journaliers", font=dict(color="#00d4ff", size=13), x=0.01),
        xaxis=dict(tickfont=dict(size=10, family="Share Tech Mono")),
        yaxis=dict(tickfont=dict(size=10, family="Share Tech Mono")))
    st.plotly_chart(fig, use_container_width=True)

    # Diversification quality
    avg_corr = (corr.values.sum() - len(tickers)) / (len(tickers) * (len(tickers) - 1))
    div_color = "#00ff88" if avg_corr < 0.3 else ("#ffd700" if avg_corr < 0.6 else "#ff3b6b")
    div_label = "BIEN DIVERSIFIÉ" if avg_corr < 0.3 else ("MODÉRÉMENT DIVERSIFIÉ" if avg_corr < 0.6 else "PEU DIVERSIFIÉ")

    metric_row([
        {"label": "Corrélation moyenne",   "value": f"{avg_corr:.3f}", "color": ""},
        {"label": "Qualité diversif.",      "value": div_label, "color": ""},
        {"label": "Nb actifs",             "value": str(len(tickers)), "color": ""},
        {"label": "Paires analysées",      "value": str(len(tickers)*(len(tickers)-1)//2), "color": ""},
    ])

    # Most / least correlated pairs
    section_title("PAIRES LES PLUS / MOINS CORRÉLÉES", "🔍")
    pairs = []
    for i in range(len(tickers)):
        for j in range(i+1, len(tickers)):
            pairs.append((tickers[i], tickers[j], float(corr.iloc[i, j])))

    pairs.sort(key=lambda x: abs(x[2]), reverse=True)
    col_hi, col_lo = st.columns(2)
    with col_hi:
        st.markdown('<div style="font-family:Rajdhani;font-size:.7rem;color:#ff3b6b;'
                    'letter-spacing:.1em;margin-bottom:6px;">🔴 PLUS CORRÉLÉS</div>',
                    unsafe_allow_html=True)
        for a, b, c in pairs[:5]:
            col_r = "#00ff88" if c > 0 else "#ff3b6b"
            st.markdown(f'<div style="font-family:Share Tech Mono;font-size:.73rem;'
                        f'padding:4px 0;border-bottom:1px solid rgba(255,255,255,.04);">'
                        f'<span style="color:#00d4ff;">{a}</span> × '
                        f'<span style="color:#00d4ff;">{b}</span>'
                        f'<span style="color:{col_r};float:right;">{c:+.3f}</span></div>',
                        unsafe_allow_html=True)
    with col_lo:
        st.markdown('<div style="font-family:Rajdhani;font-size:.7rem;color:#00ff88;'
                    'letter-spacing:.1em;margin-bottom:6px;">🟢 MOINS CORRÉLÉS</div>',
                    unsafe_allow_html=True)
        for a, b, c in sorted(pairs, key=lambda x: abs(x[2]))[:5]:
            col_r = "#00ff88" if c > 0 else "#ff3b6b"
            st.markdown(f'<div style="font-family:Share Tech Mono;font-size:.73rem;'
                        f'padding:4px 0;border-bottom:1px solid rgba(255,255,255,.04);">'
                        f'<span style="color:#00d4ff;">{a}</span> × '
                        f'<span style="color:#00d4ff;">{b}</span>'
                        f'<span style="color:{col_r};float:right;">{c:+.3f}</span></div>',
                        unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
def _compare_tab():
    section_title("COMPARAISON DES STRATÉGIES D'ALLOCATION", "📊")

    st.markdown("""
    <div style="font-family:Share Tech Mono;font-size:.73rem;color:#7a93b0;
    margin-bottom:14px;line-height:1.8;">
    Compare les stratégies : Equal Weight vs Max Sharpe vs Min Variance vs Risk Parity
    sur un univers d'actifs commun.
    </div>""", unsafe_allow_html=True)

    assets_df = load_assets()
    defaults_t = ["AAPL", "MSFT", "NVDA", "AMZN", "JPM", "GS", "GLD", "SPY"]
    ticker_opts = [f'{r["ticker"]} — {r["name"]}' for _, r in assets_df.iterrows()]
    defs = [opt for opt in ticker_opts if opt.split(" — ")[0] in defaults_t]

    selected = st.multiselect("Actifs", ticker_opts, default=defs, key="comp_assets", max_selections=12)
    tickers  = [s.split(" — ")[0] for s in selected]
    period   = st.selectbox("Période d'analyse", ["1y", "2y"], key="comp_period")
    rf       = 0.0425

    if len(tickers) < 3:
        st.warning("Sélectionnez au moins 3 actifs.")
        return

    with st.spinner("⏳ Calcul des stratégies..."):
        price_data = {}
        for t in tickers:
            h = get_history(t, period)
            if not h.empty and "Close" in h.columns:
                price_data[t] = h["Close"]

    if len(price_data) < 3:
        st.error("Données insuffisantes.")
        return

    prices_df  = pd.DataFrame(price_data).dropna()
    mu, cov    = compute_stats(prices_df)
    daily      = prices_df.pct_change().dropna()
    n          = len(prices_df.columns)

    strategies = {}
    strategies["Equal Weight"] = np.ones(n) / n

    res_sharpe = markowitz_optimize(mu, cov, rf=rf, objective="sharpe")
    if res_sharpe:
        strategies["Max Sharpe"] = np.array([res_sharpe["weights"].get(t, 0) for t in prices_df.columns])

    res_minvol = markowitz_optimize(mu, cov, rf=rf, objective="min_vol")
    if res_minvol:
        strategies["Min Variance"] = np.array([res_minvol["weights"].get(t, 0) for t in prices_df.columns])

    # Risk Parity
    vols = np.sqrt(np.diag(cov.values))
    rp_w = (1 / vols) / (1 / vols).sum()
    strategies["Risk Parity"] = rp_w

    # Performance stats
    perf_rows = []
    for name, w in strategies.items():
        port_ret = (daily.values @ w)
        cum      = (1 + port_ret).cumprod()
        ann_ret  = float((1 + np.mean(port_ret)) ** 252 - 1)
        ann_vol  = float(np.std(port_ret) * np.sqrt(252))
        sharpe   = (ann_ret - rf) / ann_vol if ann_vol > 0 else 0
        mdd      = float(((pd.Series(cum) - pd.Series(cum).cummax()) / pd.Series(cum).cummax()).min())
        perf_rows.append({"Stratégie": name, "Rendement": ann_ret, "Volatilité": ann_vol,
                          "Sharpe": sharpe, "Max DD": mdd, "weights": w, "cum": cum})

    # Cumulative performance chart
    fig = go.Figure()
    colors = ["#00d4ff", "#00ff88", "#ffd700", "#ff8c00"]
    for i, row in enumerate(perf_rows):
        fig.add_trace(go.Scatter(
            x=list(range(len(row["cum"]))), y=(row["cum"] - 1) * 100,
            name=row["Stratégie"], line=dict(color=colors[i % len(colors)], width=2),
            hovertemplate=row["Stratégie"] + "<br>%{y:.2f}%<extra></extra>"))
    fig.add_hline(y=0, line_color="rgba(255,255,255,.2)")
    fig.update_layout(**_P, height=300,
        legend=dict(orientation="h", y=1.05, font=dict(size=10)),
        xaxis=dict(title="Jours", gridcolor="rgba(255,255,255,.04)"),
        yaxis=dict(title="Performance cumulée (%)", gridcolor="rgba(255,255,255,.04)"))
    st.plotly_chart(fig, use_container_width=True)

    # Stats table
    section_title("TABLEAU COMPARATIF", "📋")
    tbl_rows = []
    for row in perf_rows:
        tbl_rows.append({
            "Stratégie":   row["Stratégie"],
            "Rendement":   f'{row["Rendement"]*100:+.2f}%',
            "Volatilité":  f'{row["Volatilité"]*100:.2f}%',
            "Sharpe":      f'{row["Sharpe"]:.3f}',
            "Max DrawDown": f'{row["Max DD"]*100:.2f}%',
        })
    st.dataframe(pd.DataFrame(tbl_rows), use_container_width=True, hide_index=True)
