# pages/trading.py  —  MAM  v3.2  FIXED
"""
Trading Desk: Spot trading + European Options (Black-Scholes + full Greeks).

FIX v3.2:
  - Options: added proper "Valider l'ordre" submit button with confirmation
  - fig.add_fill → fig.add_trace (Plotly API fix)
  - Timezone-aware datetime fix in history charts
"""
from __future__ import annotations
import math
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.ui import section_title, metric_row, pnl_cell
from utils.data import (
    get_or_init_state, persist, load_assets,
    get_price, get_price_change, get_history,
    get_multi_prices, value_portfolio, record_trade,
)
from utils.options import bs_price, bs_greeks, implied_vol, STRATEGY_META

_P = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#94a3b8", family="Share Tech Mono"),
    margin=dict(l=8, r=8, t=28, b=8),
)


def render():
    state      = get_or_init_state()
    team_id    = st.session_state.get("active_team")
    port_id    = st.session_state.get("active_portfolio")
    teams      = state.get("teams", {})

    st.markdown(
        '<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;letter-spacing:.12em;'
        'color:#00ff88;margin:0 0 2px;text-shadow:0 0 30px rgba(0,255,136,.4);">'
        '💼 TRADING DESK — MAM</h1>',
        unsafe_allow_html=True,
    )

    if not team_id or team_id not in teams:
        st.error("Sélectionnez une équipe dans la barre latérale.")
        return
    if not port_id:
        st.error("Sélectionnez un portefeuille actif dans la barre latérale.")
        return

    port = teams[team_id]["portfolios"].get(port_id)
    if not port:
        st.error(f"Portefeuille {port_id} introuvable.")
        return

    assets_df = load_assets()

    tab_spot, tab_options, tab_positions = st.tabs([
        "📈 SPOT TRADING",
        "⚙️ OPTIONS (BLACK-SCHOLES)",
        "📋 TOUTES LES POSITIONS",
    ])

    with tab_spot:
        _spot_desk(port, state, team_id, port_id, assets_df)

    with tab_options:
        _options_desk(port, state, team_id, port_id, assets_df)

    with tab_positions:
        _all_positions(teams, assets_df)


# ══════════════════════════════════════════════════════════════════════════════
#  SPOT TRADING
# ══════════════════════════════════════════════════════════════════════════════

def _spot_desk(port, state, team_id, port_id, assets_df):
    section_title("PASSER UN ORDRE SPOT", "📈")

    col_l, col_r = st.columns([1, 1])

    with col_l:
        # Asset selector
        ticker_opts = {
            f'{row["ticker"]} — {row["name"]}': row["ticker"]
            for _, row in assets_df.iterrows()
        }
        sel    = st.selectbox("Actif", list(ticker_opts.keys()), key="spot_asset")
        ticker = ticker_opts[sel]

        action = st.radio("Direction", ["🟢 ACHETER", "🔴 VENDRE"],
                          horizontal=True, key="spot_dir")
        is_buy = "ACHETER" in action

        # Live price
        price, pct = get_price_change(ticker)
        p_col = "#00ff88" if pct >= 0 else "#ff3b6b"
        p_arr = "▲" if pct >= 0 else "▼"
        sign  = "+" if pct >= 0 else ""

        st.markdown(
            f'<div style="background:rgba(0,0,0,.3);border:1px solid rgba(0,212,255,.2);'
            f'border-radius:6px;padding:10px 14px;margin:8px 0;">'
            f'<div style="font-family:Rajdhani;font-size:.68rem;color:#7a93b0;'
            f'letter-spacing:.12em;text-transform:uppercase;">Prix actuel — {ticker}</div>'
            f'<div style="font-family:Share Tech Mono;font-size:1.6rem;color:#e2e8f0;">'
            f'${price:,.4f}</div>'
            f'<div style="font-family:Share Tech Mono;font-size:.8rem;color:{p_col};">'
            f'{p_arr} {sign}{abs(pct):.2f}% vs clôture préc.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Order size
        order_type = st.radio("Type", ["Par quantité", "Par montant ($)"],
                               horizontal=True, key="spot_type")
        if order_type == "Par quantité":
            qty         = st.number_input("Quantité", min_value=0.0001, value=1.0,
                                          step=0.001, key="spot_qty", format="%.4f")
            total_order = qty * price
        else:
            amount      = st.number_input("Montant ($)", min_value=1.0,
                                          value=min(10000.0, port.get("cash", 0)),
                                          step=100.0, key="spot_amount")
            qty         = amount / price if price > 0 else 0
            total_order = amount

        # Mini chart
        hist = get_history(ticker, "1mo")
        if not hist.empty and "Close" in hist.columns:
            # FIX: strip timezone
            if hist.index.tz is not None:
                hist.index = hist.index.tz_localize(None)
            fig = go.Figure(go.Scatter(
                x=hist.index, y=hist["Close"], mode="lines",
                line=dict(color="#00d4ff" if pct >= 0 else "#ff3b6b", width=2),
                fill="tozeroy",
                fillcolor="rgba(0,212,255,.06)" if pct >= 0 else "rgba(255,59,107,.06)",
                hovertemplate="%{x|%d/%m}<br>$%{y:,.4f}<extra></extra>",
            ))
            fig.update_layout(**_P, height=140,
                xaxis=dict(showgrid=False, showticklabels=False),
                yaxis=dict(showgrid=False, tickfont=dict(size=9)))
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        # Portfolio context
        cash     = port.get("cash", 0.0)
        holdings = port.get("holdings", {})
        pos_qty  = holdings.get(ticker, {}).get("qty", 0)

        st.markdown(
            f'<div style="background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.15);'
            f'border-radius:8px;padding:14px;margin-bottom:12px;">'
            f'<div style="font-family:Rajdhani;font-size:.72rem;font-weight:700;color:#00d4ff;'
            f'letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px;">'
            f'{port.get("emoji","")} {port.get("name","")}</div>'
            f'<div style="font-family:Share Tech Mono;font-size:.8rem;color:#e2e8f0;line-height:1.8;">'
            f'Cash disponible : <b style="color:#00d4ff;">${cash:,.2f}</b><br>'
            f'Position actuelle {ticker} : <b style="color:#00d4ff;">{pos_qty:,.4f}</b><br>'
            f'Valeur de l\'ordre : <b style="color:#ffd700;">${total_order:,.2f}</b><br>'
            f'Quantité : <b style="color:#ffd700;">{qty:,.4f}</b>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # Validation
        errors = []
        if is_buy and total_order > cash + 0.01:
            errors.append(f"❌ Fonds insuffisants (cash: ${cash:,.0f}, ordre: ${total_order:,.0f})")
        if not is_buy and qty > pos_qty + 1e-6:
            errors.append(f"❌ Position insuffisante ({pos_qty:,.4f} disponibles)")
        if qty <= 0:
            errors.append("❌ Quantité invalide")

        for err in errors:
            st.markdown(
                f'<div style="background:rgba(255,59,107,.1);border:1px solid rgba(255,59,107,.3);'
                f'border-radius:4px;padding:8px 12px;font-family:Share Tech Mono;'
                f'font-size:.78rem;color:#ff3b6b;margin:4px 0;">{err}</div>',
                unsafe_allow_html=True,
            )

        # Summary
        btn_col = "#00ff88" if is_buy else "#ff3b6b"
        btn_txt = f'{"✅ ACHETER" if is_buy else "🔴 VENDRE"} {qty:,.4f} × {ticker}'

        st.markdown(
            f'<div style="background:rgba(0,0,0,.25);border:1px solid rgba(255,255,255,.08);'
            f'border-radius:6px;padding:10px 14px;margin-bottom:10px;'
            f'font-family:Share Tech Mono;font-size:.77rem;">'
            f'<div style="color:#7a93b0;margin-bottom:6px;font-family:Rajdhani;font-size:.7rem;'
            f'letter-spacing:.12em;text-transform:uppercase;">Récapitulatif</div>'
            f'Direction : <span style="color:{btn_col};font-weight:bold;">'
            f'{"ACHAT" if is_buy else "VENTE"}</span><br>'
            f'Actif : <b style="color:#00d4ff;">{ticker}</b><br>'
            f'Quantité : <b style="color:#ffd700;">{qty:,.4f}</b><br>'
            f'Prix : <b>${price:,.4f}</b><br>'
            f'Total : <b style="color:#ffd700;">${total_order:,.2f}</b>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if st.button(btn_txt, disabled=len(errors) > 0, key="spot_exec",
                     type="primary" if not errors else "secondary"):
            err = record_trade(port, ticker, "BUY" if is_buy else "SELL", qty, price)
            if err:
                st.error(err)
            else:
                st.success(f"✅ {'Achat' if is_buy else 'Vente'} exécuté : "
                           f"{qty:,.4f} × {ticker} @ ${price:,.4f}")
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  OPTIONS DESK  (Black-Scholes + full Greeks + validated submit)
# ══════════════════════════════════════════════════════════════════════════════

def _options_desk(port, state, team_id, port_id, assets_df):
    section_title("OPTIONS EUROPÉENNES — BLACK-SCHOLES", "⚙️")

    # Filter to optionable assets (equities + ETFs)
    if "category" in assets_df.columns:
        opt_mask  = assets_df["category"].isin(["Equities", "ETF", "Crypto", "Equity"])
        opt_assets = assets_df[opt_mask]
    else:
        opt_assets = assets_df
    if opt_assets.empty:
        opt_assets = assets_df

    ticker_opts = {
        f'{row["ticker"]} — {row["name"]}': row["ticker"]
        for _, row in opt_assets.head(60).iterrows()
    }

    col_l, col_r = st.columns([1, 1])

    with col_l:
        sel    = st.selectbox("Sous-jacent", list(ticker_opts.keys()), key="opt_asset")
        ticker = ticker_opts[sel]
        spot   = get_price(ticker)

        st.markdown(
            f'<div style="font-family:Share Tech Mono;font-size:.78rem;color:#7a93b0;'
            f'margin-bottom:8px;">Prix spot : <b style="color:#00d4ff;">${spot:,.4f}</b></div>',
            unsafe_allow_html=True,
        )

        opt_type   = st.radio("Type", ["call", "put"], horizontal=True, key="opt_type")
        K          = st.number_input("Strike (K)", 0.01, 1e6,
                                     max(round(spot, 2), 0.01), key="opt_K")
        T_days     = st.slider("Maturité (jours)", 1, 730, 30, key="opt_T")
        T          = T_days / 365.0
        r_rate     = st.slider("Taux sans risque (%)", 0.0, 10.0, 4.25, 0.1, key="opt_r") / 100
        sigma      = st.slider("Volatilité implicite (%)", 1.0, 150.0, 20.0, 0.5, key="opt_sig") / 100
        n_contracts = st.number_input("Nombre de contrats (×100 actions)",
                                      min_value=1, value=1, step=1, key="opt_n")

    with col_r:
        # ── Black-Scholes computation ──────────────────────────────────────────
        premium = bs_price(spot, K, T, r_rate, sigma, opt_type)
        greeks  = bs_greeks(spot, K, T, r_rate, sigma, opt_type)
        total_premium = premium * n_contracts * 100

        # Moneyness
        ratio = spot / K if K > 0 else 1.0
        if opt_type == "call":
            if ratio > 1.02:   mon, mon_col = "IN THE MONEY",  "#00ff88"
            elif ratio < 0.98: mon, mon_col = "OUT THE MONEY", "#ff3b6b"
            else:              mon, mon_col = "AT THE MONEY",  "#ffd700"
        else:
            if ratio < 0.98:   mon, mon_col = "IN THE MONEY",  "#00ff88"
            elif ratio > 1.02: mon, mon_col = "OUT THE MONEY", "#ff3b6b"
            else:              mon, mon_col = "AT THE MONEY",  "#ffd700"

        st.markdown(
            f'<div style="background:rgba(0,0,0,.3);border:1px solid rgba(0,212,255,.2);'
            f'border-radius:8px;padding:14px;margin-bottom:10px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'margin-bottom:10px;">'
            f'<div style="font-family:Rajdhani;font-size:1rem;font-weight:700;color:#00d4ff;">'
            f'PRIME (PAR ACTION)</div>'
            f'<span style="font-family:Rajdhani;font-size:.72rem;font-weight:700;'
            f'color:{mon_col};background:{mon_col}22;border:1px solid {mon_col}44;'
            f'padding:2px 8px;border-radius:3px;">{mon}</span>'
            f'</div>'
            f'<div style="font-family:Share Tech Mono;font-size:2rem;color:#7c3aed;'
            f'font-weight:bold;">${premium:,.4f}</div>'
            f'<div style="font-family:Share Tech Mono;font-size:.8rem;color:#7a93b0;'
            f'margin-top:4px;">TOTAL ({n_contracts} contrat(s)) : '
            f'<b style="color:#e2e8f0;">${total_premium:,.2f}</b></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Greeks cards
        greek_data = [
            ("Δ DELTA",  f'{greeks["delta"]:+.4f}', "Sensibilité au prix spot",  "#00d4ff"),
            ("Γ GAMMA",  f'{greeks["gamma"]:.6f}',  "Convexité du delta",        "#00ff88"),
            ("Θ THETA",  f'{greeks["theta"]:+.4f}$/j', "Décroissance temporelle", "#ff3b6b"),
            ("ν VEGA",   f'{greeks["vega"]:+.4f}$/1%', "Sensibilité à la vol",   "#ff8c00"),
            ("ρ RHO",    f'{greeks["rho"]:+.4f}$/1%',  "Sensibilité aux taux",   "#7c3aed"),
        ]
        g_cols = st.columns(2)
        for i, (gname, gval, gdesc, gcol) in enumerate(greek_data):
            val_float = float(gval.replace("+","").replace("$","").replace("/j","").replace("/1%",""))
            sign_col  = "#00ff88" if val_float >= 0 else "#ff3b6b"
            with g_cols[i % 2]:
                st.markdown(
                    f'<div style="background:rgba(0,0,0,.2);border:1px solid rgba(255,255,255,.06);'
                    f'border-radius:6px;padding:8px 10px;margin:3px 0;">'
                    f'<div style="font-family:Rajdhani;font-size:.68rem;color:{gcol};'
                    f'font-weight:700;letter-spacing:.08em;">{gname}</div>'
                    f'<div style="font-family:Share Tech Mono;font-size:.82rem;'
                    f'color:{sign_col};font-weight:bold;">{gval}</div>'
                    f'<div style="font-family:Share Tech Mono;font-size:.65rem;'
                    f'color:#475569;">{gdesc}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── Implied Vol Calculator ─────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    col_iv, col_payoff = st.columns(2)

    with col_iv:
        section_title("CALCULATEUR VOL IMPLICITE", "🔍")
        mkt_price = st.number_input(
            "Prix de marché observé ($)", 0.01, 1e6,
            max(round(premium, 4), 0.01), key="iv_mkt",
        )
        iv = implied_vol(mkt_price, spot, K, T, r_rate, opt_type)
        if iv is not None:
            iv_col = "#00ff88" if iv < sigma else "#ff3b6b"
            st.markdown(
                f'<div style="background:rgba(124,58,237,.08);border:1px solid rgba(124,58,237,.3);'
                f'border-radius:6px;padding:12px;text-align:center;">'
                f'<div style="font-family:Rajdhani;font-size:.7rem;color:#7a93b0;'
                f'letter-spacing:.15em;text-transform:uppercase;">VOL IMPLICITE</div>'
                f'<div style="font-family:Share Tech Mono;font-size:2rem;'
                f'color:{iv_col};font-weight:bold;">{iv*100:.2f}%</div>'
                f'<div style="font-family:Share Tech Mono;font-size:.72rem;color:#475569;">'
                f'vs vol entrée {sigma*100:.2f}%</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.warning("Impossible de calculer la vol implicite pour ce prix.")

    with col_payoff:
        section_title("PAYOFF À L'EXPIRATION", "📉")
        lo    = max(spot * 0.6, 0.01)
        hi    = spot * 1.4
        spots = np.linspace(lo, hi, 400)

        if opt_type == "call":
            pnl = n_contracts * 100 * (np.maximum(spots - K, 0) - premium)
        else:
            pnl = n_contracts * 100 * (np.maximum(K - spots, 0) - premium)

        pnl_pos = np.where(pnl >= 0, pnl, 0)
        pnl_neg = np.where(pnl <  0, pnl, 0)

        fig2 = go.Figure()
        # FIX: use add_trace instead of add_fill (wrong Plotly API)
        fig2.add_trace(go.Scatter(
            x=spots, y=pnl_pos, fill="tozeroy",
            fillcolor="rgba(0,255,136,.12)",
            line=dict(color="rgba(0,0,0,0)", width=0),
            showlegend=False, hoverinfo="skip",
        ))
        fig2.add_trace(go.Scatter(
            x=spots, y=pnl_neg, fill="tozeroy",
            fillcolor="rgba(255,59,107,.12)",
            line=dict(color="rgba(0,0,0,0)", width=0),
            showlegend=False, hoverinfo="skip",
        ))
        fig2.add_trace(go.Scatter(
            x=spots, y=pnl, mode="lines",
            line=dict(color="#7c3aed", width=2.5),
            name="P&L",
            hovertemplate="Spot: $%{x:.2f}<br>P&L: $%{y:,.2f}<extra></extra>",
        ))
        fig2.add_hline(y=0, line_color="rgba(255,255,255,.2)", line_width=1)
        fig2.add_vline(x=spot, line_dash="dot", line_color="#ffd700",
                       annotation_text=f"S=${spot:.1f}",
                       annotation_font_color="#ffd700")
        fig2.add_vline(x=K, line_dash="dash", line_color="rgba(255,255,255,.3)",
                       annotation_text=f"K=${K:.1f}",
                       annotation_font_color="rgba(255,255,255,.5)")
        # Breakeven
        sign_changes = np.where(np.diff(np.sign(pnl)))[0]
        for idx in sign_changes:
            be = (spots[idx] + spots[idx + 1]) / 2
            fig2.add_vline(x=be, line_color="#ff8c00", line_dash="dot",
                           annotation_text=f"BE ${be:.1f}",
                           annotation_font_color="#ff8c00",
                           annotation_position="bottom right")
        fig2.update_layout(**_P, height=220,
            xaxis=dict(title="Prix ($)", gridcolor="rgba(255,255,255,.04)"),
            yaxis=dict(title="P&L ($)", gridcolor="rgba(255,255,255,.04)"))
        st.plotly_chart(fig2, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    #  OPTIONS ORDER  — FIX: proper submit button with validation
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("<br>", unsafe_allow_html=True)
    section_title("PASSER UN ORDRE SUR OPTION", "✅")

    opt_action = st.radio(
        "Sens de l'ordre",
        ["🟢 ACHETER (Long)", "🔴 VENDRE (Short / Write)"],
        horizontal=True, key="opt_action",
    )
    is_buy_opt  = "ACHETER" in opt_action
    cost_or_rec = total_premium  # positive = cost if buying, revenue if selling
    cash        = port.get("cash", 0.0)

    # Option position summary
    col_sum1, col_sum2 = st.columns(2)
    with col_sum1:
        st.markdown(
            f'<div style="background:rgba(0,0,0,.25);border:1px solid rgba(255,255,255,.08);'
            f'border-radius:6px;padding:12px 14px;font-family:Share Tech Mono;font-size:.8rem;">'
            f'<div style="color:#7a93b0;font-family:Rajdhani;font-size:.7rem;'
            f'letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px;">'
            f'Récapitulatif option</div>'
            f'Sens : <span style="color:{"#00ff88" if is_buy_opt else "#ff3b6b"};font-weight:bold;">'
            f'{"LONG (Acheteur)" if is_buy_opt else "SHORT (Vendeur)"}</span><br>'
            f'Type : <b style="color:#7c3aed;">{opt_type.upper()}</b><br>'
            f'Sous-jacent : <b style="color:#00d4ff;">{ticker}</b><br>'
            f'Strike : <b>K = ${K:,.2f}</b><br>'
            f'Maturité : <b>{T_days} jours ({T:.3f} an)</b><br>'
            f'Vol. impl. : <b>{sigma*100:.1f}%</b><br>'
            f'Contrats : <b style="color:#ffd700;">{n_contracts} × 100 = {n_contracts*100} actions</b><br>'
            f'Prime / action : <b style="color:#7c3aed;">${premium:,.4f}</b><br>'
            f'<b style="color:#ffd700;">{"Coût total" if is_buy_opt else "Prime reçue"} : '
            f'${total_premium:,.2f}</b>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_sum2:
        # Risk/reward summary
        if opt_type == "call" and is_buy_opt:
            max_loss = total_premium
            max_gain = "Illimité"
            be_price = K + premium
        elif opt_type == "put" and is_buy_opt:
            max_loss = total_premium
            max_gain = f"${(K - premium) * n_contracts * 100:,.0f}"
            be_price = K - premium
        elif opt_type == "call" and not is_buy_opt:
            max_loss = "Illimité"
            max_gain = total_premium
            be_price = K + premium
        else:  # put + short
            max_loss = f"${(K - premium) * n_contracts * 100:,.0f}"
            max_gain = total_premium
            be_price = K - premium

        st.markdown(
            f'<div style="background:rgba(124,58,237,.06);border:1px solid rgba(124,58,237,.2);'
            f'border-radius:6px;padding:12px 14px;font-family:Share Tech Mono;font-size:.8rem;">'
            f'<div style="color:#7a93b0;font-family:Rajdhani;font-size:.7rem;'
            f'letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px;">'
            f'Profil risque/rendement</div>'
            f'Gain max : <span style="color:#00ff88;font-weight:bold;">'
            f'{max_gain if isinstance(max_gain, str) else f"${max_gain:,.2f}"}</span><br>'
            f'Perte max : <span style="color:#ff3b6b;font-weight:bold;">'
            f'{max_loss if isinstance(max_loss, str) else f"${max_loss:,.2f}"}</span><br>'
            f'Seuil de rentabilité : <span style="color:#ff8c00;">${be_price:,.2f}</span><br>'
            f'Cash disponible : <span style="color:#00d4ff;">${cash:,.2f}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Validation errors
    opt_errors = []
    if is_buy_opt and total_premium > cash + 0.01:
        opt_errors.append(
            f"❌ Fonds insuffisants pour payer la prime "
            f"(besoin: ${total_premium:,.2f}, cash: ${cash:,.2f})"
        )
    if n_contracts <= 0:
        opt_errors.append("❌ Nombre de contrats invalide")
    if K <= 0:
        opt_errors.append("❌ Strike invalide (K > 0 requis)")

    for err in opt_errors:
        st.markdown(
            f'<div style="background:rgba(255,59,107,.1);border:1px solid rgba(255,59,107,.3);'
            f'border-radius:4px;padding:8px 12px;font-family:Share Tech Mono;'
            f'font-size:.78rem;color:#ff3b6b;margin:4px 0;">{err}</div>',
            unsafe_allow_html=True,
        )

    # ── THE FIX: actual submit button for options ──────────────────────────────
    btn_label = (
        f'{"✅ ACHETER" if is_buy_opt else "🔴 VENDRE"} '
        f'{n_contracts} contrat(s) {opt_type.upper()} '
        f'K=${K:.2f} — Prime ${total_premium:,.2f}'
    )

    if st.button(btn_label, disabled=len(opt_errors) > 0, key="opt_submit", type="primary"):
        # Record option position
        opt_positions = port.setdefault("options", [])
        opt_positions.append({
            "date":        datetime.now().strftime("%Y-%m-%d %H:%M"),
            "ticker":      ticker,
            "type":        opt_type,
            "action":      "BUY" if is_buy_opt else "SELL",
            "strike":      round(K, 4),
            "maturity_days": T_days,
            "sigma":       round(sigma * 100, 2),
            "n_contracts": n_contracts,
            "premium":     round(premium, 6),
            "total_premium": round(total_premium, 2),
            "spot_at_entry": round(spot, 4),
        })

        # Deduct/add premium from/to cash
        if is_buy_opt:
            port["cash"] = port.get("cash", 0) - total_premium
        else:
            port["cash"] = port.get("cash", 0) + total_premium

        # Record as trade
        port.setdefault("trades", []).append({
            "date":   datetime.now().strftime("%Y-%m-%d %H:%M"),
            "ticker": f"{ticker} {opt_type.upper()} K={K:.2f}",
            "action": "BUY OPTION" if is_buy_opt else "SELL OPTION",
            "qty":    n_contracts,
            "price":  round(premium, 6),
            "total":  round(total_premium, 2),
        })

        persist()
        action_str = "Achat" if is_buy_opt else "Vente"
        st.success(
            f"✅ {action_str} option exécuté : {n_contracts} contrat(s) "
            f"{opt_type.upper()} K=${K:.2f} sur {ticker} | "
            f"Prime : ${total_premium:,.2f}"
        )
        st.rerun()

    # ── Existing option positions ──────────────────────────────────────────────
    opt_pos = port.get("options", [])
    if opt_pos:
        st.markdown("<br>", unsafe_allow_html=True)
        section_title("POSITIONS OPTIONS OUVERTES", "📋")
        opt_df = pd.DataFrame(opt_pos)
        st.dataframe(opt_df, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
#  ALL POSITIONS (cross-portfolio view)
# ══════════════════════════════════════════════════════════════════════════════

def _all_positions(teams, assets_df):
    section_title("TOUTES LES POSITIONS — PORTEFEUILLE ACTIF", "📋")

    team_id = st.session_state.get("active_team")
    port_id = st.session_state.get("active_portfolio")

    if not team_id or not port_id:
        st.info("Sélectionnez un portefeuille.")
        return

    port = teams.get(team_id, {}).get("portfolios", {}).get(port_id, {})
    if not port:
        st.info("Portefeuille introuvable.")
        return

    holdings = port.get("holdings", {})
    if not holdings:
        st.info("Aucune position spot ouverte. Rendez-vous sur l'onglet Spot Trading.")
        return

    tickers = tuple(holdings.keys())
    prices  = get_multi_prices(tickers)

    hdr = ["Ticker", "Quantité", "Px moy.", "Px actuel", "Var. 1j",
           "Valeur marché", "P&L ($)", "P&L (%)"]
    th  = "".join(
        f'<th style="font-family:Rajdhani;font-size:.66rem;color:#00d4ff;'
        f'letter-spacing:.09em;text-transform:uppercase;padding:7px 9px;'
        f'background:rgba(0,212,255,.06);border-bottom:1px solid rgba(0,212,255,.15);">'
        f'{c}</th>' for c in hdr)

    tbody = ""
    total_val = 0.0
    total_pnl = 0.0

    for ticker, pos in holdings.items():
        qty = pos.get("qty", 0)
        avg = pos.get("avg_price", 0.0)
        curr, pct_d = prices.get(ticker, (avg, 0.0))
        mkt  = qty * curr
        cost = qty * avg
        pnl  = mkt - cost
        ppct = pnl / cost * 100 if cost else 0.0

        total_val += mkt
        total_pnl += pnl

        pc   = "pnl-pos" if pnl > 0 else ("pnl-neg" if pnl < 0 else "pnl-zero")
        vc   = "pnl-pos" if pct_d > 0 else ("pnl-neg" if pct_d < 0 else "pnl-zero")
        sg   = "+" if pnl > 0 else ""
        ar   = "▲" if pnl > 0 else ("▼" if pnl < 0 else "▬")
        vr   = "▲" if pct_d > 0 else ("▼" if pct_d < 0 else "▬")

        tbody += (
            f'<tr style="border-bottom:1px solid rgba(255,255,255,.03);">'
            f'<td style="padding:7px 9px;color:#00d4ff;font-weight:bold;">{ticker}</td>'
            f'<td style="padding:7px 9px;">{qty:,.4f}</td>'
            f'<td style="padding:7px 9px;color:#7a93b0;">${avg:,.4f}</td>'
            f'<td style="padding:7px 9px;">${curr:,.4f}</td>'
            f'<td style="padding:7px 9px;" class="{vc}">{vr} {abs(pct_d):.2f}%</td>'
            f'<td style="padding:7px 9px;">${mkt:,.0f}</td>'
            f'<td style="padding:7px 9px;" class="{pc}">{sg}${abs(pnl):,.2f}</td>'
            f'<td style="padding:7px 9px;" class="{pc}">{ar} {abs(ppct):.2f}%</td>'
            f'</tr>'
        )

    # Totals footer
    tc   = "pnl-pos" if total_pnl > 0 else ("pnl-neg" if total_pnl < 0 else "pnl-zero")
    tsg  = "+" if total_pnl > 0 else ""
    tbody += (
        f'<tr style="background:rgba(0,212,255,.05);border-top:1px solid rgba(0,212,255,.2);">'
        f'<td colspan="5" style="padding:7px 9px;font-family:Rajdhani;font-size:.78rem;'
        f'color:#7a93b0;letter-spacing:.1em;text-transform:uppercase;">'
        f'TOTAL ({len(holdings)} positions)</td>'
        f'<td style="padding:7px 9px;color:#e2e8f0;font-weight:bold;">${total_val:,.0f}</td>'
        f'<td style="padding:7px 9px;" class="{tc}">{tsg}${abs(total_pnl):,.2f}</td>'
        f'<td></td>'
        f'</tr>'
    )

    st.markdown(
        f'<div style="overflow-x:auto;border:1px solid rgba(0,212,255,.15);border-radius:8px;">'
        f'<table style="width:100%;border-collapse:collapse;font-family:Share Tech Mono;'
        f'font-size:.78rem;color:#e2e8f0;">'
        f'<thead><tr>{th}</tr></thead><tbody>{tbody}</tbody></table></div>',
        unsafe_allow_html=True,
    )

    # Recent trades
    section_title("HISTORIQUE DES TRANSACTIONS", "🔄")
    trades = port.get("trades", [])
    if trades:
        df = pd.DataFrame(trades[-30:][::-1])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune transaction enregistrée.")
