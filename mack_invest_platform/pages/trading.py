# pages/trading.py  —  MAM v3.3
"""
Trading Desk avec validation par typologie de portefeuille.
Si l'actif choisi ne correspond pas aux classes d'actifs autorisées → BLOQUÉ.
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
from utils.options import bs_price, bs_greeks, implied_vol

_P = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#94a3b8", family="Share Tech Mono"),
    margin=dict(l=8, r=8, t=28, b=8),
)

# ── Contraintes par type d'actif (cohérent avec dashboard.py) ────────────────
_ASSET_CONSTRAINTS = {
    "equity":    {"emoji":"📊","name":"Actions",           "max_single":30, "allowed_suffix":[],       "forbidden_suffix":["-USD","=F","=X"]},
    "etf":       {"emoji":"🗂️","name":"ETFs / Indices",    "max_single":50, "allowed_suffix":[],       "forbidden_suffix":["-USD","=F","=X"]},
    "crypto":    {"emoji":"₿", "name":"Crypto",            "max_single":15, "allowed_suffix":["-USD"], "forbidden_suffix":[]},
    "commodity": {"emoji":"🛢️","name":"Matières premières","max_single":20, "allowed_suffix":["=F"],   "forbidden_suffix":[]},
    "forex":     {"emoji":"💱","name":"Forex",              "max_single":15, "allowed_suffix":["=X"],   "forbidden_suffix":[]},
    "bond":      {"emoji":"📜","name":"Obligations",        "max_single":25, "allowed_suffix":[],       "forbidden_suffix":["-USD","=F","=X"]},
    "mixed":     {"emoji":"🌐","name":"Multi-actifs",       "max_single":25, "allowed_suffix":[],       "forbidden_suffix":[]},
}

_BOND_TICKERS = {"TLT","IEF","LQD","HYG","SHY","BND","AGG","GOVT","VCSH","VCIT"}
_ETF_TICKERS  = {"SPY","QQQ","IWM","VTI","EEM","EWJ","GLD","SLV","USO","ARKK",
                  "XLF","XLE","XLV","XLK","XLI","XLB","XLU","XLRE","XLP","XLY",
                  "VNQ","VUG","VTV","VO","VB","VEA","VWO"}


def _infer_asset_class(ticker: str) -> str:
    if ticker.endswith("-USD"):
        return "crypto"
    if ticker.endswith("=F"):
        return "commodity"
    if ticker.endswith("=X"):
        return "forex"
    if ticker in _BOND_TICKERS:
        return "bond"
    if ticker in _ETF_TICKERS or ticker.startswith("^"):
        return "etf"
    return "equity"


def _validate_ticker_for_portfolio(ticker: str, port: dict, prices_dict: dict, qty: float, price: float) -> list[str]:
    """
    Valide qu'un ticker est compatible avec les contraintes du portefeuille.
    Retourne une liste d'erreurs (vide = OK).
    """
    errors = []
    asset_types = port.get("asset_types", [])

    # Si pas de types définis (ancien portefeuille) → pas de validation
    if not asset_types:
        return errors

    # Classe de l'actif
    asset_class = _infer_asset_class(ticker)

    # Cas "mixed" = tout autorisé sauf > 25% par position
    if "mixed" in asset_types:
        holdings = port.get("holdings", {})
        cash     = port.get("cash", 0.0)
        total_mkt = sum(
            pos.get("qty",0) * prices_dict.get(tk, pos.get("avg_price",0))
            for tk, pos in holdings.items()
        )
        total_val = total_mkt + cash
        new_val   = qty * price
        pct_new   = new_val / (total_val + new_val) * 100 if (total_val + new_val) > 0 else 0
        if pct_new > 25:
            errors.append(f"🌐 Multi-actifs : max 25% par position ({pct_new:.1f}% demandé)")
        return errors

    # Vérifier que la classe est autorisée
    if asset_class not in asset_types:
        allowed_names = [_ASSET_CONSTRAINTS.get(t,{}).get("name", t) for t in asset_types]
        errors.append(
            f"❌ **{ticker}** est classé comme **{asset_class}** "
            f"— non autorisé dans ce portefeuille.\n\n"
            f"Classes autorisées : **{', '.join(allowed_names)}**"
        )
        return errors  # Inutile de continuer si classe refusée

    # Vérifier le % max par position
    cst = _ASSET_CONSTRAINTS.get(asset_class, {})
    max_single = cst.get("max_single", 100)
    holdings   = port.get("holdings", {})
    cash       = port.get("cash", 0.0)
    total_mkt  = sum(
        pos.get("qty",0) * prices_dict.get(tk, pos.get("avg_price",0))
        for tk, pos in holdings.items()
    )
    total_val  = total_mkt + cash
    new_val    = qty * price
    pct_new    = new_val / (total_val + new_val) * 100 if (total_val + new_val) > 0 else 0
    if pct_new > max_single:
        errors.append(
            f"⚠️ **{ticker}** ({asset_class}) : {pct_new:.1f}% du portefeuille "
            f"> max autorisé ({max_single}%) pour cette classe."
        )

    return errors


def render():
    state   = get_or_init_state()
    team_id = st.session_state.get("active_team")
    port_id = st.session_state.get("active_portfolio")
    teams   = state.get("teams", {})

    st.markdown(
        '<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;letter-spacing:.12em;'
        'color:#00ff88;margin:0 0 2px;text-shadow:0 0 30px rgba(0,255,136,.4);">'
        '💼 TRADING DESK — MAM</h1>', unsafe_allow_html=True)

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

    # ── Bannière de stratégie & contraintes ───────────────────────────────────
    asset_types = port.get("asset_types", [])
    strategy    = port.get("strategy", "")
    if asset_types:
        types_html = " &nbsp;·&nbsp; ".join(
            f'<span style="color:#00ff88;">{_ASSET_CONSTRAINTS.get(t,{}).get("emoji","")} {_ASSET_CONSTRAINTS.get(t,{}).get("name",t)}</span>'
            for t in asset_types
        )
        st.markdown(
            f'<div style="background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.2);'
            f'border-radius:8px;padding:10px 16px;margin-bottom:12px;'
            f'font-family:Share Tech Mono;font-size:.76rem;">'
            f'<span style="color:#7a93b0;">Portefeuille :</span> '
            f'<b style="color:#e2e8f0;">{port.get("emoji","💼")} {port.get("name","")}</b> '
            f'&nbsp;|&nbsp; <span style="color:#7a93b0;">Stratégie :</span> '
            f'<b style="color:#ffd700;">{strategy}</b> '
            f'&nbsp;|&nbsp; <span style="color:#7a93b0;">Classes autorisées :</span> {types_html}'
            f'</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div style="background:rgba(255,215,0,.04);border:1px solid rgba(255,215,0,.15);'
            f'border-radius:8px;padding:10px 16px;margin-bottom:12px;'
            f'font-family:Share Tech Mono;font-size:.76rem;color:#7a93b0;">'
            f'⚠️ Portefeuille sans contraintes de type (ancien format). '
            f'Toutes les classes d\'actifs sont acceptées.</div>', unsafe_allow_html=True)

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
#  SPOT TRADING  avec validation par typologie
# ══════════════════════════════════════════════════════════════════════════════

def _spot_desk(port, state, team_id, port_id, assets_df):
    section_title("PASSER UN ORDRE SPOT", "📈")

    col_l, col_r = st.columns([1, 1])

    with col_l:
        ticker_opts = {
            f'{row["ticker"]} — {row.get("name", row["ticker"])}': row["ticker"]
            for _, row in assets_df.iterrows()
        }
        sel    = st.selectbox("Actif", list(ticker_opts.keys()), key="spot_asset")
        ticker = ticker_opts[sel]

        # ── Classe détectée + compatibilité ──────────────────────────────────
        asset_class = _infer_asset_class(ticker)
        asset_types = port.get("asset_types", [])
        cst         = _ASSET_CONSTRAINTS.get(asset_class, {})
        is_allowed  = (not asset_types) or ("mixed" in asset_types) or (asset_class in asset_types)

        class_col = "#00ff88" if is_allowed else "#ff3b6b"
        class_ico = cst.get("emoji","")
        class_nm  = cst.get("name", asset_class)
        st.markdown(
            f'<div style="font-family:Share Tech Mono;font-size:.72rem;margin:4px 0 8px;">'
            f'Classe détectée : <span style="color:{class_col};font-weight:bold;">'
            f'{class_ico} {class_nm}</span>'
            f'{"" if is_allowed else " &nbsp;⛔ NON AUTORISÉ dans ce portefeuille"}'
            f'</div>', unsafe_allow_html=True)

        action = st.radio("Direction", ["🟢 ACHETER", "🔴 VENDRE"], horizontal=True, key="spot_dir")
        is_buy = "ACHETER" in action

        price, pct = get_price_change(ticker)
        p_col = "#00ff88" if pct >= 0 else "#ff3b6b"
        p_arr = "▲" if pct >= 0 else "▼"
        sign  = "+" if pct >= 0 else ""

        st.markdown(
            f'<div style="background:rgba(0,0,0,.3);border:1px solid rgba(0,212,255,.2);'
            f'border-radius:6px;padding:10px 14px;margin:8px 0;">'
            f'<div style="font-family:Rajdhani;font-size:.68rem;color:#7a93b0;letter-spacing:.12em;">Prix actuel — {ticker}</div>'
            f'<div style="font-family:Share Tech Mono;font-size:1.6rem;color:#e2e8f0;">${price:,.4f}</div>'
            f'<div style="font-family:Share Tech Mono;font-size:.8rem;color:{p_col};">{p_arr} {sign}{abs(pct):.2f}% vs clôture préc.</div>'
            f'</div>', unsafe_allow_html=True)

        order_type = st.radio("Type", ["Par quantité","Par montant ($)"], horizontal=True, key="spot_type")
        if order_type == "Par quantité":
            qty         = st.number_input("Quantité", min_value=0.0001, value=1.0, step=0.001, key="spot_qty", format="%.4f")
            total_order = qty * price
        else:
            amount      = st.number_input("Montant ($)", min_value=1.0, value=min(10000.0, port.get("cash",0)), step=100.0, key="spot_amount")
            qty         = amount / price if price > 0 else 0
            total_order = amount

        hist = get_history(ticker, "1mo")
        if not hist.empty and "Close" in hist.columns:
            if hist.index.tz is not None:
                hist.index = hist.index.tz_localize(None)
            fig = go.Figure(go.Scatter(
                x=hist.index, y=hist["Close"], mode="lines",
                line=dict(color="#00d4ff" if pct >= 0 else "#ff3b6b", width=2),
                fill="tozeroy",
                fillcolor="rgba(0,212,255,.06)" if pct >= 0 else "rgba(255,59,107,.06)",
            ))
            fig.update_layout(**_P, height=140,
                xaxis=dict(showgrid=False, showticklabels=False),
                yaxis=dict(showgrid=False, tickfont=dict(size=9)))
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        cash    = port.get("cash", 0.0)
        holdings = port.get("holdings", {})
        pos_qty = holdings.get(ticker, {}).get("qty", 0)

        st.markdown(
            f'<div style="background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.15);'
            f'border-radius:8px;padding:14px;margin-bottom:12px;">'
            f'<div style="font-family:Rajdhani;font-size:.72rem;font-weight:700;color:#00d4ff;letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px;">{port.get("emoji","")} {port.get("name","")}</div>'
            f'<div style="font-family:Share Tech Mono;font-size:.8rem;color:#e2e8f0;line-height:1.8;">'
            f'Cash disponible : <b style="color:#00d4ff;">${cash:,.2f}</b><br>'
            f'Position {ticker} : <b style="color:#00d4ff;">{pos_qty:,.4f}</b><br>'
            f'Valeur de l\'ordre : <b style="color:#ffd700;">${total_order:,.2f}</b><br>'
            f'Quantité : <b style="color:#ffd700;">{qty:,.4f}</b>'
            f'</div></div>', unsafe_allow_html=True)

        # ── Validation ────────────────────────────────────────────────────────
        errors = []

        # 1. Vérification classe d'actif (BLOQUE si non autorisé)
        if is_buy:
            # Construire un dict prix simplifié pour la validation
            prices_simple = {tk: pos.get("avg_price",0) for tk, pos in holdings.items()}
            prices_simple[ticker] = price
            type_errors = _validate_ticker_for_portfolio(ticker, port, prices_simple, qty, price)
            errors.extend(type_errors)

        # 2. Vérifications financières
        if is_buy and total_order > cash + 0.01:
            errors.append(f"❌ Fonds insuffisants (cash: ${cash:,.0f}, ordre: ${total_order:,.0f})")
        if not is_buy and qty > pos_qty + 1e-6:
            errors.append(f"❌ Position insuffisante ({pos_qty:,.4f} disponibles)")
        if qty <= 0:
            errors.append("❌ Quantité invalide")

        # Affichage erreurs
        for err in errors:
            st.markdown(
                f'<div style="background:rgba(255,59,107,.1);border:1px solid rgba(255,59,107,.3);'
                f'border-radius:6px;padding:10px 14px;font-family:Share Tech Mono;'
                f'font-size:.78rem;color:#ff3b6b;margin:4px 0;line-height:1.6;">{err}</div>',
                unsafe_allow_html=True)

        # ── Récapitulatif ─────────────────────────────────────────────────────
        btn_col = "#00ff88" if is_buy else "#ff3b6b"
        btn_txt = f'{"✅ ACHETER" if is_buy else "🔴 VENDRE"} {qty:,.4f} × {ticker}'
        st.markdown(
            f'<div style="background:rgba(0,0,0,.25);border:1px solid rgba(255,255,255,.08);'
            f'border-radius:6px;padding:10px 14px;margin-bottom:10px;font-family:Share Tech Mono;font-size:.77rem;">'
            f'<div style="color:#7a93b0;font-family:Rajdhani;font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;margin-bottom:6px;">Récapitulatif</div>'
            f'Direction : <span style="color:{btn_col};font-weight:bold;">{"ACHAT" if is_buy else "VENTE"}</span><br>'
            f'Actif : <b style="color:#00d4ff;">{ticker}</b> '
            f'<span style="color:{class_col};">({class_ico} {class_nm})</span><br>'
            f'Quantité : <b style="color:#ffd700;">{qty:,.4f}</b><br>'
            f'Prix : <b>${price:,.4f}</b><br>'
            f'Total : <b style="color:#ffd700;">${total_order:,.2f}</b>'
            f'</div>', unsafe_allow_html=True)

        if st.button(btn_txt, disabled=len(errors) > 0, key="spot_exec", type="primary" if not errors else "secondary"):
            err = record_trade(port, ticker, "BUY" if is_buy else "SELL", qty, price)
            if err:
                st.error(err)
            else:
                st.success(f"✅ {'Achat' if is_buy else 'Vente'} exécuté : {qty:,.4f} × {ticker} @ ${price:,.4f}")
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  OPTIONS DESK  (Black-Scholes)
# ══════════════════════════════════════════════════════════════════════════════

def _options_desk(port, state, team_id, port_id, assets_df):
    section_title("OPTIONS EUROPÉENNES — BLACK-SCHOLES", "⚙️")

    if "category" in assets_df.columns:
        opt_assets = assets_df[assets_df["category"].isin(["Equities","ETF","Crypto","Equity"])]
    else:
        opt_assets = assets_df
    if opt_assets.empty:
        opt_assets = assets_df

    ticker_opts = {f'{row["ticker"]} — {row.get("name",row["ticker"])}': row["ticker"] for _, row in opt_assets.head(60).iterrows()}
    col_l, col_r = st.columns([1, 1])

    with col_l:
        sel    = st.selectbox("Sous-jacent", list(ticker_opts.keys()), key="opt_asset")
        ticker = ticker_opts[sel]
        spot   = get_price(ticker)
        st.markdown(f'<div style="font-family:Share Tech Mono;font-size:.78rem;color:#7a93b0;margin-bottom:8px;">Prix spot : <b style="color:#00d4ff;">${spot:,.4f}</b></div>', unsafe_allow_html=True)
        opt_type    = st.radio("Type", ["call","put"], horizontal=True, key="opt_type")
        K           = st.number_input("Strike (K)", 0.01, 1e6, max(round(spot,2),0.01), key="opt_K")
        T_days      = st.slider("Maturité (jours)", 1, 730, 30, key="opt_T")
        T           = T_days / 365.0
        r_rate      = st.slider("Taux sans risque (%)", 0.0, 10.0, 4.25, 0.1, key="opt_r") / 100
        sigma       = st.slider("Volatilité implicite (%)", 1.0, 150.0, 20.0, 0.5, key="opt_sig") / 100
        n_contracts = st.number_input("Contrats (×100)", min_value=1, value=1, step=1, key="opt_n")

    with col_r:
        premium       = bs_price(spot, K, T, r_rate, sigma, opt_type)
        greeks        = bs_greeks(spot, K, T, r_rate, sigma, opt_type)
        total_premium = premium * n_contracts * 100
        ratio = spot / K if K > 0 else 1.0
        if opt_type == "call":
            mon, mon_col = ("IN THE MONEY","#00ff88") if ratio>1.02 else (("OUT THE MONEY","#ff3b6b") if ratio<0.98 else ("AT THE MONEY","#ffd700"))
        else:
            mon, mon_col = ("IN THE MONEY","#00ff88") if ratio<0.98 else (("OUT THE MONEY","#ff3b6b") if ratio>1.02 else ("AT THE MONEY","#ffd700"))
        st.markdown(
            f'<div style="background:rgba(0,0,0,.3);border:1px solid rgba(0,212,255,.2);border-radius:8px;padding:14px;margin-bottom:10px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
            f'<div style="font-family:Rajdhani;font-size:1rem;font-weight:700;color:#00d4ff;">PRIME / ACTION</div>'
            f'<span style="font-family:Rajdhani;font-size:.72rem;font-weight:700;color:{mon_col};background:{mon_col}22;border:1px solid {mon_col}44;padding:2px 8px;border-radius:3px;">{mon}</span>'
            f'</div>'
            f'<div style="font-family:Share Tech Mono;font-size:2rem;color:#7c3aed;font-weight:bold;">${premium:,.4f}</div>'
            f'<div style="font-family:Share Tech Mono;font-size:.8rem;color:#7a93b0;margin-top:4px;">TOTAL ({n_contracts} contrat(s)) : <b style="color:#e2e8f0;">${total_premium:,.2f}</b></div>'
            f'</div>', unsafe_allow_html=True)
        greek_data = [
            ("Δ DELTA",f'{greeks["delta"]:+.4f}',"#00d4ff"),
            ("Γ GAMMA",f'{greeks["gamma"]:.6f}',"#00ff88"),
            ("Θ THETA",f'{greeks["theta"]:+.4f}$/j',"#ff3b6b"),
            ("ν VEGA", f'{greeks["vega"]:+.4f}$/1%',"#ff8c00"),
            ("ρ RHO",  f'{greeks["rho"]:+.4f}$/1%',"#7c3aed"),
        ]
        g_cols = st.columns(2)
        for i,(gname,gval,gcol) in enumerate(greek_data):
            try:
                vf = float(gval.replace("+","").replace("$","").replace("/j","").replace("/1%",""))
                sc = "#00ff88" if vf>=0 else "#ff3b6b"
            except Exception:
                sc = gcol
            with g_cols[i%2]:
                st.markdown(
                    f'<div style="background:rgba(0,0,0,.2);border:1px solid rgba(255,255,255,.06);border-radius:6px;padding:8px 10px;margin:3px 0;">'
                    f'<div style="font-family:Rajdhani;font-size:.68rem;color:{gcol};font-weight:700;">{gname}</div>'
                    f'<div style="font-family:Share Tech Mono;font-size:.82rem;color:{sc};font-weight:bold;">{gval}</div>'
                    f'</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_iv, col_payoff = st.columns(2)
    with col_iv:
        section_title("VOL IMPLICITE", "🔍")
        mkt_price = st.number_input("Prix de marché observé ($)", 0.01, 1e6, max(round(premium,4),0.01), key="iv_mkt")
        iv = implied_vol(mkt_price, spot, K, T, r_rate, opt_type)
        if iv is not None:
            iv_col = "#00ff88" if iv < sigma else "#ff3b6b"
            st.markdown(
                f'<div style="background:rgba(124,58,237,.08);border:1px solid rgba(124,58,237,.3);border-radius:6px;padding:12px;text-align:center;">'
                f'<div style="font-family:Rajdhani;font-size:.7rem;color:#7a93b0;letter-spacing:.15em;">VOL IMPLICITE</div>'
                f'<div style="font-family:Share Tech Mono;font-size:2rem;color:{iv_col};font-weight:bold;">{iv*100:.2f}%</div>'
                f'<div style="font-family:Share Tech Mono;font-size:.72rem;color:#475569;">vs vol entrée {sigma*100:.2f}%</div>'
                f'</div>', unsafe_allow_html=True)
        else:
            st.warning("Calcul vol implicite impossible pour ce prix.")

    with col_payoff:
        section_title("PAYOFF À L'EXPIRATION", "📉")
        spots_ = np.linspace(max(spot*0.6,0.01), spot*1.4, 400)
        if opt_type == "call":
            pnl_ = n_contracts*100*(np.maximum(spots_-K,0)-premium)
        else:
            pnl_ = n_contracts*100*(np.maximum(K-spots_,0)-premium)
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=spots_,y=np.where(pnl_>=0,pnl_,0),fill="tozeroy",fillcolor="rgba(0,255,136,.12)",line=dict(color="rgba(0,0,0,0)",width=0),showlegend=False,hoverinfo="skip"))
        fig2.add_trace(go.Scatter(x=spots_,y=np.where(pnl_<0,pnl_,0),fill="tozeroy",fillcolor="rgba(255,59,107,.12)",line=dict(color="rgba(0,0,0,0)",width=0),showlegend=False,hoverinfo="skip"))
        fig2.add_trace(go.Scatter(x=spots_,y=pnl_,mode="lines",line=dict(color="#7c3aed",width=2.5),hovertemplate="Spot: $%{x:.2f}<br>P&L: $%{y:,.2f}<extra></extra>"))
        fig2.add_hline(y=0,line_color="rgba(255,255,255,.2)")
        fig2.add_vline(x=spot,line_dash="dot",line_color="#ffd700",annotation_text=f"S={spot:.1f}",annotation_font_color="#ffd700")
        fig2.add_vline(x=K,line_dash="dash",line_color="rgba(255,255,255,.3)",annotation_text=f"K={K:.1f}",annotation_font_color="rgba(255,255,255,.5)")
        fig2.update_layout(**_P, height=220,
            xaxis=dict(title="Prix ($)",gridcolor="rgba(255,255,255,.04)"),
            yaxis=dict(title="P&L ($)",gridcolor="rgba(255,255,255,.04)"))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    section_title("PASSER UN ORDRE OPTION", "✅")
    opt_action = st.radio("Sens", ["🟢 ACHETER (Long)","🔴 VENDRE (Short)"], horizontal=True, key="opt_action")
    is_buy_opt = "ACHETER" in opt_action
    cash       = port.get("cash", 0.0)
    opt_errors = []
    if is_buy_opt and total_premium > cash + 0.01:
        opt_errors.append(f"❌ Fonds insuffisants (besoin: ${total_premium:,.2f}, cash: ${cash:,.2f})")
    btn_label = f'{"✅ ACHETER" if is_buy_opt else "🔴 VENDRE"} {n_contracts} contrat(s) {opt_type.upper()} K=${K:.2f} — ${total_premium:,.2f}'
    for err in opt_errors:
        st.markdown(f'<div style="background:rgba(255,59,107,.1);border:1px solid rgba(255,59,107,.3);border-radius:4px;padding:8px 12px;font-family:Share Tech Mono;font-size:.78rem;color:#ff3b6b;margin:4px 0;">{err}</div>', unsafe_allow_html=True)
    if st.button(btn_label, disabled=len(opt_errors)>0, key="opt_submit", type="primary"):
        port.setdefault("options",[]).append({
            "date":datetime.now().strftime("%Y-%m-%d %H:%M"),"ticker":ticker,"type":opt_type,
            "action":"BUY" if is_buy_opt else "SELL","strike":round(K,4),"maturity_days":T_days,
            "sigma":round(sigma*100,2),"n_contracts":n_contracts,"premium":round(premium,6),
            "total_premium":round(total_premium,2),"spot_at_entry":round(spot,4),
        })
        port["cash"] = port.get("cash",0) + (-total_premium if is_buy_opt else total_premium)
        port.setdefault("trades",[]).append({
            "date":datetime.now().strftime("%Y-%m-%d %H:%M"),
            "ticker":f"{ticker} {opt_type.upper()} K={K:.2f}",
            "action":"BUY OPTION" if is_buy_opt else "SELL OPTION",
            "qty":n_contracts,"price":round(premium,6),"total":round(total_premium,2),
        })
        persist()
        st.success(f"✅ Option exécutée : {n_contracts} × {opt_type.upper()} K=${K:.2f} sur {ticker}")
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  ALL POSITIONS
# ══════════════════════════════════════════════════════════════════════════════

def _all_positions(teams, assets_df):
    section_title("TOUTES LES POSITIONS", "📋")
    team_id = st.session_state.get("active_team")
    port_id = st.session_state.get("active_portfolio")
    if not team_id or not port_id:
        st.info("Sélectionnez un portefeuille.")
        return
    port = teams.get(team_id,{}).get("portfolios",{}).get(port_id,{})
    if not port:
        st.info("Portefeuille introuvable.")
        return
    holdings = port.get("holdings",{})
    if not holdings:
        st.info("Aucune position spot. Tradez depuis l'onglet Spot Trading.")
        return

    tickers = tuple(holdings.keys())
    prices  = get_multi_prices(tickers)
    hdr = ["Ticker","Quantité","Px moy.","Px actuel","Var. 1j","Valeur marché","P&L ($)","P&L (%)"]
    th  = "".join(f'<th style="font-family:Rajdhani;font-size:.66rem;color:#00d4ff;letter-spacing:.09em;text-transform:uppercase;padding:7px 9px;background:rgba(0,212,255,.06);border-bottom:1px solid rgba(0,212,255,.15);">{c}</th>' for c in hdr)
    tbody = ""; total_val = total_pnl = 0.0
    for ticker, pos in holdings.items():
        qty=pos.get("qty",0); avg=pos.get("avg_price",0.0)
        curr,pct_d = prices.get(ticker,(avg,0.0))
        mkt=qty*curr; cost=qty*avg; pnl=mkt-cost; ppct=pnl/cost*100 if cost else 0.0
        total_val+=mkt; total_pnl+=pnl
        pc = "#00ff88" if pnl>0 else ("#ff3b6b" if pnl<0 else "#94a3b8")
        dc = "#00ff88" if pct_d>0 else ("#ff3b6b" if pct_d<0 else "#94a3b8")
        sg = "+" if pnl>0 else ""; ar = "▲" if pnl>0 else ("▼" if pnl<0 else "▬")
        vr = "▲" if pct_d>0 else ("▼" if pct_d<0 else "▬"); sgd = "+" if pct_d>0 else ""
        tbody += (
            f'<tr style="border-bottom:1px solid rgba(255,255,255,.03);">'
            f'<td style="padding:7px 9px;color:#00d4ff;font-weight:bold;">{ticker}</td>'
            f'<td style="padding:7px 9px;">{qty:,.4f}</td>'
            f'<td style="padding:7px 9px;color:#7a93b0;">${avg:,.4f}</td>'
            f'<td style="padding:7px 9px;">${curr:,.4f}</td>'
            f'<td style="padding:7px 9px;color:{dc};">{vr} {sgd}{abs(pct_d):.2f}%</td>'
            f'<td style="padding:7px 9px;">${mkt:,.0f}</td>'
            f'<td style="padding:7px 9px;color:{pc};font-weight:bold;">{sg}${abs(pnl):,.2f}</td>'
            f'<td style="padding:7px 9px;color:{pc};">{ar} {abs(ppct):.2f}%</td>'
            f'</tr>'
        )
    tc = "#00ff88" if total_pnl>0 else ("#ff3b6b" if total_pnl<0 else "#94a3b8")
    tsg = "+" if total_pnl>0 else ""
    tbody += (
        f'<tr style="background:rgba(0,212,255,.05);border-top:1px solid rgba(0,212,255,.2);">'
        f'<td colspan="5" style="padding:7px 9px;font-family:Rajdhani;font-size:.78rem;color:#7a93b0;letter-spacing:.1em;text-transform:uppercase;">TOTAL ({len(holdings)} positions)</td>'
        f'<td style="padding:7px 9px;color:#e2e8f0;font-weight:bold;">${total_val:,.0f}</td>'
        f'<td style="padding:7px 9px;color:{tc};font-weight:bold;">{tsg}${abs(total_pnl):,.2f}</td>'
        f'<td></td></tr>'
    )
    st.markdown(
        f'<div style="overflow-x:auto;border:1px solid rgba(0,212,255,.15);border-radius:8px;">'
        f'<table style="width:100%;border-collapse:collapse;font-family:Share Tech Mono;font-size:.78rem;color:#e2e8f0;">'
        f'<thead><tr>{th}</tr></thead><tbody>{tbody}</tbody></table></div>',
        unsafe_allow_html=True)

    section_title("HISTORIQUE DES TRANSACTIONS", "🔄")
    trades = port.get("trades",[])
    if trades:
        st.dataframe(pd.DataFrame(trades[-30:][::-1]), use_container_width=True, hide_index=True)
    else:
        st.info("Aucune transaction enregistrée.")
