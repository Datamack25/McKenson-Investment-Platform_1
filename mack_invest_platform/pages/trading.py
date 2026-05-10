# pages/trading.py  —  MAM Trading Desk
"""
Spot trading (BUY/SELL) + European Options with Black-Scholes pricing,
full Greeks, and order ticket.
"""
from __future__ import annotations
import math
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from components.ui import section_title, metric_row, pnl_cell
from utils.data import (
    get_or_init_state, persist, load_assets,
    get_multi_prices, get_price, get_history, record_trade,
    value_portfolio,
)
from utils.options import bs_price, bs_greeks, implied_vol, build_strategy_legs, payoff_at_expiry, STRATEGY_META

_P = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
          font=dict(color="#94a3b8", family="Share Tech Mono"),
          margin=dict(l=8, r=8, t=28, b=8))


def render():
    state    = get_or_init_state()
    team_id  = st.session_state.get("active_team")
    port_id  = st.session_state.get("active_portfolio")
    teams    = state.get("teams", {})

    st.markdown(
        '<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;letter-spacing:.12em;'
        'color:#00d4ff;margin:0 0 2px;text-shadow:0 0 30px rgba(0,212,255,.4);">'
        '💼 TRADING DESK — MAM</h1>', unsafe_allow_html=True)

    if not team_id or not port_id:
        st.warning("⚠️ Sélectionnez une équipe et un portefeuille dans la barre latérale.")
        return

    port = teams[team_id]["portfolios"].get(port_id, {})

    tab_spot, tab_options, tab_book = st.tabs([
        "📈 SPOT TRADING",
        "🎯 OPTIONS (Black-Scholes)",
        "📋 CARNET D'ORDRES",
    ])

    with tab_spot:
        _spot_trading(port, state, team_id, port_id)

    with tab_options:
        _options_desk(port, state, team_id, port_id)

    with tab_book:
        _order_book(port)


# ─────────────────────────────────────────────────────────────────────────────
def _spot_trading(port, state, team_id, port_id):
    section_title("TRADING SPOT — ACHAT / VENTE", "📈")

    assets_df = load_assets()
    categories = sorted(assets_df["category"].unique()) if not assets_df.empty else []

    col_filter, col_search = st.columns([2, 3])
    with col_filter:
        cat = st.selectbox("Catégorie", ["Tous"] + categories, key="tr_cat")
    with col_search:
        search = st.text_input("Rechercher un ticker ou nom", "", key="tr_search",
                               placeholder="ex: AAPL, Bitcoin, Gold...")

    # Filter assets
    df = assets_df.copy()
    if cat != "Tous":
        df = df[df["category"] == cat]
    if search:
        mask = (df["ticker"].str.contains(search, case=False, na=False) |
                df["name"].str.contains(search, case=False, na=False))
        df = df[mask]

    if df.empty:
        st.info("Aucun actif trouvé.")
        return

    tickers = tuple(df["ticker"].tolist())
    prices_raw = get_multi_prices(tickers)

    # Asset selector
    options_map = {
        f'{row["ticker"]} — {row["name"]} ({row["category"]})': row["ticker"]
        for _, row in df.iterrows()
    }
    selected_label = st.selectbox("Sélectionner l'actif", list(options_map.keys()), key="tr_asset")
    ticker = options_map[selected_label]
    price, pct = prices_raw.get(ticker, (0.0, 0.0))

    asset_row = df[df["ticker"] == ticker].iloc[0]

    # Live price display
    col1, col2, col3, col4, col5 = st.columns(5)
    pct_color = "#00ff88" if pct >= 0 else "#ff3b6b"
    arr = "▲" if pct >= 0 else "▼"

    def _mini_card(col, label, value, color="#e2e8f0"):
        with col:
            st.markdown(
                f'<div style="background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.15);'
                f'border-radius:6px;padding:10px;text-align:center;">'
                f'<div style="font-family:Rajdhani;font-size:.65rem;color:#7a93b0;'
                f'letter-spacing:.1em;text-transform:uppercase;">{label}</div>'
                f'<div style="font-family:Share Tech Mono;font-size:1rem;color:{color};font-weight:bold;">{value}</div>'
                f'</div>', unsafe_allow_html=True)

    _mini_card(col1, "Ticker", ticker, "#00d4ff")
    _mini_card(col2, "Prix actuel",
               f'{"$" if asset_row["currency"]=="USD" else ""}{price:,.4f} {asset_row["currency"]}',
               "#e2e8f0")
    _mini_card(col3, "Variation", f'{arr} {abs(pct):.2f}%', pct_color)
    _mini_card(col4, "Exchange", asset_row.get("exchange", "—"), "#7a93b0")
    _mini_card(col5, "Catégorie", asset_row.get("category", "—"), "#a78bfa")

    st.markdown("<br>", unsafe_allow_html=True)

    # Price history sparkline
    hist = get_history(ticker, "1mo")
    if not hist.empty and "Close" in hist.columns:
        fig_spark = go.Figure()
        fig_spark.add_trace(go.Scatter(
            x=hist.index, y=hist["Close"],
            mode="lines", line=dict(color="#00d4ff", width=1.5),
            fill="tozeroy", fillcolor="rgba(0,212,255,.06)",
            hovertemplate="%{x|%d %b}<br>$%{y:,.2f}<extra></extra>"))
        fig_spark.update_layout(**_P, height=120,
            xaxis=dict(showgrid=False, showticklabels=True),
            yaxis=dict(showgrid=False, showticklabels=True))
        st.plotly_chart(fig_spark, use_container_width=True)

    st.markdown("---")
    section_title("TICKET D'ORDRE", "🎫")

    # Portfolio info
    holdings = port.get("holdings", {})
    cash = port.get("cash", 0.0)
    current_qty = holdings.get(ticker, {}).get("qty", 0.0)
    avg_price   = holdings.get(ticker, {}).get("avg_price", 0.0)

    c1, c2, c3 = st.columns(3)
    with c1:
        action = st.radio("Direction", ["BUY", "SELL"], horizontal=True, key="tr_action")
    with c2:
        max_qty = (cash / price) if (action == "BUY" and price > 0) else current_qty
        qty_input = st.number_input(
            "Quantité", min_value=0.0001, max_value=max(max_qty, 0.0001),
            value=min(1.0, max(max_qty, 0.0001)), step=0.001,
            format="%.4f", key="tr_qty")
    with c3:
        order_total = qty_input * price
        st.markdown(
            f'<div style="background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.15);'
            f'border-radius:6px;padding:14px;margin-top:4px;">'
            f'<div style="font-family:Rajdhani;font-size:.65rem;color:#7a93b0;letter-spacing:.1em;">TOTAL ORDRE</div>'
            f'<div style="font-family:Share Tech Mono;font-size:1.3rem;color:#ffd700;font-weight:bold;">'
            f'${order_total:,.2f}</div>'
            f'<div style="font-family:Share Tech Mono;font-size:.7rem;color:#7a93b0;">'
            f'Cash dispo: ${cash:,.0f} | Position: {current_qty:,.4f}</div>'
            f'</div>', unsafe_allow_html=True)

    btn_color = "#00ff88" if action == "BUY" else "#ff3b6b"
    btn_label = f"{'🟢 ACHETER' if action=='BUY' else '🔴 VENDRE'} {qty_input:,.4f} {ticker} @ ${price:,.4f}"

    if st.button(btn_label, key="tr_exec", use_container_width=True):
        err = record_trade(port, ticker, action, qty_input, price)
        if err:
            st.error(f"❌ Erreur : {err}")
        else:
            state["teams"][team_id]["portfolios"][port_id] = port
            persist()
            st.success(f"✅ Ordre exécuté : {action} {qty_input:,.4f} {ticker} @ ${price:,.4f}")
            st.rerun()

    # Portfolio position summary
    if current_qty > 0:
        unreal_pnl = (price - avg_price) * current_qty
        pnl_pct    = (price - avg_price) / avg_price * 100 if avg_price else 0
        st.markdown("<br>", unsafe_allow_html=True)
        section_title(f"POSITION EXISTANTE — {ticker}", "📊")
        metric_row([
            {"label": "Quantité détenue", "value": f"{current_qty:,.4f}", "color": ""},
            {"label": "Prix moyen",       "value": f"${avg_price:,.4f}", "color": ""},
            {"label": "Valeur de marché", "value": f"${current_qty*price:,.2f}", "color": ""},
            {"label": "P&L non réalisé",  "value": f"${unreal_pnl:+,.2f} ({pnl_pct:+.2f}%)",
             "color": "positive" if unreal_pnl >= 0 else "negative"},
        ])


# ─────────────────────────────────────────────────────────────────────────────
def _options_desk(port, state, team_id, port_id):
    section_title("OPTIONS EUROPÉENNES — BLACK-SCHOLES", "🎯")

    st.markdown("""
    <div style="background:rgba(124,58,237,.06);border:1px solid rgba(124,58,237,.25);
    border-radius:8px;padding:12px 16px;margin-bottom:16px;font-family:Share Tech Mono;
    font-size:.75rem;color:#94a3b8;line-height:1.8;">
    🎯 <b style="color:#a78bfa;">Pricing Black-Scholes</b> — Options européennes uniquement.<br>
    Pricer basé sur le modèle de Black-Scholes 1973 avec les Grecques complètes (Δ, Γ, Θ, ν, ρ).
    </div>""", unsafe_allow_html=True)

    assets_df = load_assets()
    # Only tradeable spot underlyings (no indices futures, no forex for options)
    opt_assets = assets_df[assets_df["category"].isin(["Equities", "ETF", "Crypto"])]

    col1, col2 = st.columns([1, 1])

    with col1:
        section_title("PARAMÈTRES DE L'OPTION", "⚙️")
        tickers_opts = {f'{r["ticker"]} — {r["name"]}': r["ticker"]
                        for _, r in opt_assets.iterrows()}
        sel = st.selectbox("Sous-jacent", list(tickers_opts.keys()), key="opt_underlying")
        underlying = tickers_opts[sel]

        price = get_price(underlying)
        st.markdown(
            f'<div style="font-family:Share Tech Mono;font-size:.8rem;color:#00d4ff;margin:4px 0 10px;">'
            f'Prix spot : <b>${price:,.4f}</b></div>', unsafe_allow_html=True)

        opt_type = st.radio("Type", ["call", "put"], horizontal=True, key="opt_type")
        K   = st.number_input("Strike (K)", min_value=0.01,
                               value=round(price * 1.0, 2), step=0.5, key="opt_K")
        T_days = st.slider("Maturité (jours)", 1, 730, 30, key="opt_T")
        T   = T_days / 365.0
        r   = st.slider("Taux sans risque (%)", 0.0, 10.0, 4.25, 0.05, key="opt_r") / 100
        sig = st.slider("Volatilité implicite (%)", 1.0, 200.0, 25.0, 0.5, key="opt_sig") / 100
        n_contracts = st.number_input("Nombre de contrats (×100 actions)", 1, 1000, 1, key="opt_n")

    with col2:
        section_title("RÉSULTATS BLACK-SCHOLES", "📊")
        premium = bs_price(price, K, T, r, sig, opt_type)
        greeks  = bs_greeks(price, K, T, r, sig, opt_type)
        total_premium = premium * 100 * n_contracts

        # Moneyness
        moneyness = price / K
        if abs(moneyness - 1) < 0.02:
            money_lbl, money_col = "AT THE MONEY", "#ffd700"
        elif (opt_type == "call" and moneyness > 1) or (opt_type == "put" and moneyness < 1):
            money_lbl, money_col = "IN THE MONEY", "#00ff88"
        else:
            money_lbl, money_col = "OUT OF THE MONEY", "#ff3b6b"

        st.markdown(
            f'<div style="text-align:center;margin-bottom:12px;">'
            f'<span style="background:rgba(0,212,255,.1);border:1px solid rgba(0,212,255,.3);'
            f'border-radius:4px;padding:3px 12px;font-family:Rajdhani;font-size:.75rem;'
            f'color:{money_col};font-weight:700;letter-spacing:.12em;">{money_lbl}</span>'
            f'</div>', unsafe_allow_html=True)

        metric_row([
            {"label": "Prime (par action)", "value": f"${premium:,.4f}", "color": ""},
            {"label": f"Total ({n_contracts} contrat{'s' if n_contracts>1 else ''})",
             "value": f"${total_premium:,.2f}", "color": ""},
        ])
        st.markdown("<br>", unsafe_allow_html=True)

        # Greeks display
        g = greeks
        def greek_card(name, val, unit="", desc=""):
            col = "#00ff88" if val > 0 else ("#ff3b6b" if val < 0 else "#ffd700")
            return (f'<div style="background:rgba(0,0,0,.2);border:1px solid rgba(255,255,255,.06);'
                    f'border-radius:6px;padding:10px;margin:4px 0;">'
                    f'<div style="font-family:Rajdhani;font-size:.65rem;color:#7a93b0;letter-spacing:.1em;">{name}</div>'
                    f'<div style="font-family:Share Tech Mono;font-size:1.05rem;color:{col};font-weight:bold;">'
                    f'{val:+.4f}{unit}</div>'
                    f'<div style="font-family:Share Tech Mono;font-size:.65rem;color:#475569;">{desc}</div>'
                    f'</div>')

        st.markdown(
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">'
            + greek_card("Δ DELTA",  g["delta"], "",    "Sensibilité au prix spot")
            + greek_card("Γ GAMMA",  g["gamma"], "",    "Convexité du delta")
            + greek_card("Θ THETA",  g["theta"], "$/j", "Décroissance temporelle")
            + greek_card("ν VEGA",   g["vega"],  "/$%", "Sensibilité à la vol.")
            + greek_card("ρ RHO",    g["rho"],   "/$%", "Sensibilité aux taux")
            + '</div>', unsafe_allow_html=True)

        # Implied vol calculator
        st.markdown("<br>", unsafe_allow_html=True)
        section_title("CALCULATEUR VOL IMPLICITE", "🔍")
        mkt_price = st.number_input("Prix de marché observé ($)", 0.01, 10000.0,
                                     max(premium, 0.01), 0.01, key="opt_mkt_px")
        iv = implied_vol(mkt_price, price, K, T, r, opt_type)
        if iv:
            st.markdown(
                f'<div style="background:rgba(124,58,237,.08);border:1px solid rgba(124,58,237,.3);'
                f'border-radius:6px;padding:10px;text-align:center;">'
                f'<div style="font-family:Rajdhani;font-size:.68rem;color:#7a93b0;letter-spacing:.1em;">VOL IMPLICITE</div>'
                f'<div style="font-family:Share Tech Mono;font-size:1.8rem;color:#a78bfa;font-weight:bold;">'
                f'{iv*100:.2f}%</div></div>', unsafe_allow_html=True)
        else:
            st.warning("Vol. implicite incalculable avec ces paramètres.")

    # Payoff diagram
    st.markdown("<br>", unsafe_allow_html=True)
    section_title("DIAGRAMME DE PAYOFF À L'EXPIRATION", "📉")
    spots = np.linspace(max(price * 0.5, 0.01), price * 1.5, 300)
    leg   = [{"type": opt_type, "K": K, "qty": 1, "premium": premium}]
    pnl   = payoff_at_expiry(leg, spots)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=spots, y=pnl,
        mode="lines", line=dict(color="#00d4ff", width=2.5),
        fill="tozeroy", fillcolor="rgba(0,212,255,.06)",
        hovertemplate="Spot: $%{x:,.2f}<br>P&L: $%{y:,.2f}<extra></extra>"))
    fig.add_hline(y=0, line_color="rgba(255,255,255,.3)", line_dash="dot")
    fig.add_vline(x=price, line_color="#ffd700", line_dash="dash",
                  annotation_text=f"Spot ${price:,.2f}", annotation_font_color="#ffd700")
    fig.add_vline(x=K, line_color="#ff3b6b", line_dash="dot",
                  annotation_text=f"Strike ${K:,.2f}", annotation_font_color="#ff3b6b")
    fig.update_layout(**_P, height=280,
        xaxis=dict(title="Prix spot à l'expiration ($)", gridcolor="rgba(255,255,255,.04)"),
        yaxis=dict(title="P&L par action ($)", gridcolor="rgba(255,255,255,.04)"))
    st.plotly_chart(fig, use_container_width=True)

    # Options strategy payoff
    st.markdown("<br>", unsafe_allow_html=True)
    section_title("STRATÉGIES OPTIONS — PAYOFF MULTI-JAMBES", "🧩")
    strategy_names = list(STRATEGY_META.keys())
    strat_sel = st.selectbox("Stratégie", strategy_names, key="opt_strat")
    strat_sig2 = st.slider("Volatilité stratégie (%)", 5.0, 100.0, 25.0, 0.5, key="opt_sig2") / 100
    T_strat    = st.slider("Maturité stratégie (jours)", 7, 365, 60, key="opt_T2") / 365.0

    legs   = build_strategy_legs(strat_sel, price, K, T_strat, r, strat_sig2)
    spots2 = np.linspace(max(price * 0.6, 0.01), price * 1.4, 400)
    pnl2   = payoff_at_expiry(legs, spots2)

    meta = STRATEGY_META.get(strat_sel, {})
    st.markdown(
        f'<div style="background:rgba(0,0,0,.2);border-left:3px solid {meta.get("color","#00d4ff")};'
        f'padding:8px 14px;margin-bottom:10px;font-family:Share Tech Mono;font-size:.75rem;color:#94a3b8;">'
        f'<b style="color:{meta.get("color","#00d4ff")};">{meta.get("cat","")}</b> — {meta.get("use","")}'
        f'</div>', unsafe_allow_html=True)

    color = meta.get("color", "#00d4ff")
    fig2 = go.Figure()
    # Color positive/negative areas
    pnl2_pos = np.where(pnl2 >= 0, pnl2, 0)
    pnl2_neg = np.where(pnl2 < 0, pnl2, 0)
    fig2.add_trace(go.Scatter(x=spots2, y=pnl2,
        mode="lines", line=dict(color=color, width=2.5),
        hovertemplate="Spot: $%{x:,.2f}<br>P&L: $%{y:,.2f}<extra></extra>"))
    fig2.add_fill = go.Scatter(x=spots2, y=pnl2_pos, fill="tozeroy",
        fillcolor="rgba(0,255,136,.07)", line=dict(width=0), showlegend=False)
    fig2.add_hline(y=0, line_color="rgba(255,255,255,.3)")
    fig2.add_vline(x=price, line_color="#ffd700", line_dash="dash",
                   annotation_text=f"Spot ${price:,.2f}", annotation_font_color="#ffd700")
    fig2.update_layout(**_P, height=280,
        title=dict(text=strat_sel, font=dict(size=13, color=color), x=0.01),
        xaxis=dict(title="Prix spot à l'expiration ($)", gridcolor="rgba(255,255,255,.04)"),
        yaxis=dict(title="P&L ($)", gridcolor="rgba(255,255,255,.04)"))
    st.plotly_chart(fig2, use_container_width=True)

    # Legs detail table
    section_title("DÉTAIL DES JAMBES", "📋")
    legs_data = []
    for i, leg in enumerate(legs):
        prem = leg.get("premium", 0)
        legs_data.append({
            "Jambe": i + 1,
            "Type": leg["type"].upper(),
            "Direction": "LONG" if leg.get("qty", 1) > 0 else "SHORT",
            "Strike": f"${leg.get('K', price):,.2f}" if leg["type"] != "stock" else "—",
            "Prime": f"${prem:,.4f}",
            "Coût / Crédit": f'{"Débit" if leg.get("qty",1)>0 else "Crédit"} ${abs(prem):,.4f}',
        })
    if legs_data:
        df_legs = pd.DataFrame(legs_data)
        st.dataframe(df_legs, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
def _order_book(port):
    section_title("HISTORIQUE DES TRANSACTIONS", "📋")

    trades = port.get("trades", [])
    if not trades:
        st.info("Aucune transaction enregistrée. Commencez à trader !")
        return

    df = pd.DataFrame(trades[::-1])

    # Stats
    buys  = df[df["action"] == "BUY"]
    sells = df[df["action"] == "SELL"]
    metric_row([
        {"label": "Total trades",    "value": str(len(df)), "color": ""},
        {"label": "Achats (BUY)",    "value": str(len(buys)), "color": "positive"},
        {"label": "Ventes (SELL)",   "value": str(len(sells)), "color": "negative"},
        {"label": "Volume total",    "value": f'${df["total"].sum():,.0f}', "color": ""},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    # Styled dataframe
    def style_action(val):
        if val == "BUY":
            return "color: #00ff88; font-weight: bold;"
        elif val == "SELL":
            return "color: #ff3b6b; font-weight: bold;"
        return ""

    # Build HTML table
    hdr = ["Date", "Ticker", "Action", "Quantité", "Prix", "Total"]
    th  = "".join(
        f'<th style="font-family:Rajdhani;font-size:.67rem;color:#00d4ff;'
        f'letter-spacing:.1em;text-transform:uppercase;padding:7px 10px;'
        f'background:rgba(0,212,255,.06);border-bottom:1px solid rgba(0,212,255,.18);">'
        f'{c}</th>' for c in hdr)

    tbody = ""
    for _, row in df.iterrows():
        act_col = "#00ff88" if row.get("action") == "BUY" else "#ff3b6b"
        tbody += (
            f'<tr style="border-bottom:1px solid rgba(255,255,255,.04);">'
            f'<td style="padding:7px 10px;color:#7a93b0;font-size:.76rem;">{row.get("date","—")}</td>'
            f'<td style="padding:7px 10px;color:#00d4ff;font-weight:bold;">{row.get("ticker","—")}</td>'
            f'<td style="padding:7px 10px;color:{act_col};font-weight:bold;">{row.get("action","—")}</td>'
            f'<td style="padding:7px 10px;">{row.get("qty",0):,.4f}</td>'
            f'<td style="padding:7px 10px;">${row.get("price",0):,.4f}</td>'
            f'<td style="padding:7px 10px;color:#ffd700;">${row.get("total",0):,.2f}</td>'
            f'</tr>'
        )

    st.markdown(
        f'<div class="mam-table-wrap"><table class="mam-table">'
        f'<thead><tr>{th}</tr></thead><tbody>{tbody}</tbody></table></div>',
        unsafe_allow_html=True)

    # Trade volume over time
    if len(df) > 1 and "date" in df.columns:
        st.markdown("<br>", unsafe_allow_html=True)
        section_title("VOLUME PAR DATE", "📊")
        try:
            df["date_only"] = pd.to_datetime(df["date"]).dt.date
            vol_by_date = df.groupby("date_only")["total"].sum().reset_index()
            fig = go.Figure(go.Bar(
                x=vol_by_date["date_only"].astype(str),
                y=vol_by_date["total"],
                marker_color="rgba(0,212,255,.6)",
                hovertemplate="%{x}<br>Volume: $%{y:,.0f}<extra></extra>"))
            fig.update_layout(**_P, height=200,
                xaxis=dict(showgrid=False),
                yaxis=dict(title="Volume ($)", gridcolor="rgba(255,255,255,.04)"))
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass
