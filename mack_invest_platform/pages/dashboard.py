# pages/dashboard.py  —  MAM Dashboard  v3.3
"""
FIXES v3.3:
  - N'affiche QUE les portefeuilles avec trades OU holdings (pas les placeholders vides)
  - P&L calculé depuis prix live yfinance vs avg_price réel (pas 0% ni 100%)
  - Colonnes "Prix achat" et "Prix live" séparées
  - Aucun tableau si aucun portefeuille actif
"""
from __future__ import annotations
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st
from datetime import datetime

from components.ui import section_title, metric_row, pnl_cell
from utils.data import (
    get_or_init_state, get_multi_prices, value_portfolio,
    compute_risk_metrics, persist,
)

_P = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#94a3b8", family="Share Tech Mono"),
    margin=dict(l=8, r=8, t=28, b=8),
)


def _has_activity(port: dict) -> bool:
    """Un portefeuille est 'actif' seulement s'il a des trades OU des positions."""
    return bool(port.get("trades")) or bool(port.get("holdings"))


def _normalize_prices(raw: dict) -> dict[str, float]:
    """get_multi_prices retourne {ticker: (price, pct)} → {ticker: float}."""
    out = {}
    for t, v in raw.items():
        if isinstance(v, (list, tuple)) and len(v) >= 1:
            p = v[0]
        else:
            p = v
        out[t] = float(p) if (p == p) else float("nan")
    return out


def render():
    st.markdown(
        '<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;letter-spacing:.12em;'
        'color:#00d4ff;margin:52px 0 4px;text-shadow:0 0 30px rgba(0,212,255,.4);">'
        '🏠 DASHBOARD — MAM</h1>',
        unsafe_allow_html=True,
    )

    state   = get_or_init_state()
    teams   = state.get("teams", {})
    team_id = st.session_state.get("active_team")
    port_id = st.session_state.get("active_portfolio")

    if not teams:
        st.info("Aucune équipe configurée. Visitez le panneau Admin.")
        return

    # Pré-fetch prix live pour tous les tickers actifs
    all_tickers: set[str] = set()
    for t in teams.values():
        for p in t.get("portfolios", {}).values():
            if _has_activity(p):
                all_tickers.update(p.get("holdings", {}).keys())

    prices_dict: dict[str, float] = {}
    if all_tickers:
        with st.spinner("⏳ Chargement des prix live…"):
            prices_dict = _normalize_prices(get_multi_prices(tuple(all_tickers)))

    view = st.radio(
        "Vue", ["🌐 Vue globale", "📊 Portefeuille actif"],
        horizontal=True, key="dash_view",
    )
    st.markdown("<br>", unsafe_allow_html=True)

    if view == "🌐 Vue globale":
        _global_view(teams, prices_dict)
    else:
        if not team_id or not port_id:
            st.warning("⚠️ Sélectionnez une équipe et un portefeuille dans la barre latérale.")
            return
        port = teams.get(team_id, {}).get("portfolios", {}).get(port_id)
        team = teams.get(team_id, {})
        if port is None:
            st.error("Portefeuille introuvable.")
            return
        if not _has_activity(port):
            st.info("📭 Ce portefeuille n'a aucune activité. Effectuez votre premier trade depuis le Trading Desk.")
            return
        _portfolio_view(team, team_id, port, port_id, prices_dict, state)


# ── Global view ───────────────────────────────────────────────────────────────
def _global_view(teams: dict, prices_dict: dict):
    section_title("VUE GLOBALE", "🌐")

    all_rows = []
    team_agg = []

    for tid, team in teams.items():
        team_total = 0.0
        team_init  = 0.0
        for pid, port in team.get("portfolios", {}).items():
            if not _has_activity(port):          # ← filtre strict
                continue
            val   = value_portfolio(port, prices_dict)
            total = val["total"]
            init  = float(port.get("initial_cash", 1_000_000))
            pnl   = total - init
            pct   = pnl / init * 100 if init else 0
            all_rows.append({
                "team": team["name"], "team_emoji": team.get("emoji", ""),
                "port": port["name"], "port_emoji": port.get("emoji", "💼"),
                "strategy": port.get("strategy", "Libre"),
                "total": total, "init": init, "pnl": pnl, "pct": pct,
                "n_trades":    len(port.get("trades", [])),
                "n_positions": len(val["positions"]),
                "cash":        val["cash"],
            })
            team_total += total
            team_init  += init
        if team_total > 0 or team_init > 0:
            team_agg.append({
                "name": team["name"], "emoji": team.get("emoji", ""),
                "total": team_total,
                "pnl":  team_total - team_init,
                "pct":  (team_total - team_init) / team_init * 100 if team_init else 0,
            })

    if not all_rows:
        st.info("Aucun portefeuille actif pour le moment. Effectuez vos premiers trades depuis le Trading Desk.")
        return

    # KPI strip
    total_aum  = sum(r["total"] for r in all_rows)
    total_pnl  = sum(r["pnl"]   for r in all_rows)
    total_init = sum(r["init"]  for r in all_rows)
    total_pct  = total_pnl / total_init * 100 if total_init else 0

    metric_row([
        {"label": "AUM Total",      "value": f"${total_aum:,.0f}",  "color": ""},
        {"label": "P&L Total",      "value": f"${total_pnl:+,.0f}",
         "color": "positive" if total_pnl >= 0 else "negative"},
        {"label": "Rendement moy.", "value": f"{total_pct:+.2f}%",
         "color": "positive" if total_pct >= 0 else "negative"},
        {"label": "Portefeuilles actifs", "value": str(len(all_rows)), "color": ""},
    ])
    st.markdown("<br>", unsafe_allow_html=True)

    # Barres P&L par équipe
    team_agg_sorted = sorted(team_agg, key=lambda x: x["pct"], reverse=True)
    col_chart, col_rank = st.columns([3, 2])
    with col_chart:
        section_title("P&L PAR ÉQUIPE", "📊")
        fig = go.Figure(go.Bar(
            x=[f'{t["emoji"]} {t["name"]}' for t in team_agg_sorted],
            y=[t["pct"] for t in team_agg_sorted],
            marker_color=["rgba(0,255,136,.7)" if t["pct"] >= 0 else "rgba(255,59,107,.7)"
                          for t in team_agg_sorted],
            text=[f'{"+" if t["pct"]>=0 else ""}{t["pct"]:.2f}%' for t in team_agg_sorted],
            textposition="outside",
        ))
        fig.add_hline(y=0, line_color="rgba(255,255,255,.2)")
        fig.update_layout(**_P, height=240,
            xaxis=dict(showgrid=False),
            yaxis=dict(title="P&L (%)", gridcolor="rgba(255,255,255,.04)"))
        st.plotly_chart(fig, use_container_width=True)

    with col_rank:
        section_title("CLASSEMENT", "🏆")
        for i, t in enumerate(team_agg_sorted):
            medal   = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
            col_    = "#00ff88" if t["pct"] >= 0 else "#ff3b6b"
            sign    = "+" if t["pct"] >= 0 else ""
            st.markdown(
                f'<div style="background:rgba(0,0,0,.2);border:1px solid rgba(255,255,255,.06);'
                f'border-radius:6px;padding:8px 12px;margin-bottom:6px;'
                f'display:flex;justify-content:space-between;align-items:center;">'
                f'<span style="font-family:Rajdhani;font-size:.9rem;font-weight:700;color:#e2e8f0;">'
                f'{medal} {t["emoji"]} {t["name"]}</span>'
                f'<span style="font-family:Share Tech Mono;font-size:.85rem;color:{col_};font-weight:bold;">'
                f'{sign}{t["pct"]:.2f}%</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Tableau portefeuilles actifs
    section_title("PORTEFEUILLES ACTIFS", "📋")
    all_rows_sorted = sorted(all_rows, key=lambda x: x["pct"], reverse=True)
    hdr = ["#", "Équipe", "Portefeuille", "Stratégie",
           "Valeur", "P&L ($)", "P&L (%)", "Cash", "Pos.", "Trades"]
    th  = "".join(
        f'<th style="font-family:Rajdhani;font-size:.60rem;color:#00d4ff;'
        f'letter-spacing:.08em;text-transform:uppercase;padding:7px 9px;'
        f'background:rgba(0,212,255,.06);border-bottom:1px solid rgba(0,212,255,.18);">'
        f'{c}</th>' for c in hdr)
    tbody = ""
    for i, r in enumerate(all_rows_sorted, 1):
        c_  = "#00ff88" if r["pnl"] >= 0 else "#ff3b6b"
        arr = "▲" if r["pnl"] > 0 else "▼"
        sgn = "+" if r["pnl"] >= 0 else ""
        med = ["🥇","🥈","🥉"][i-1] if i <= 3 else str(i)
        tbody += (
            f'<tr style="border-bottom:1px solid rgba(255,255,255,.04);">'
            f'<td style="padding:6px 10px;text-align:center;">{med}</td>'
            f'<td style="padding:6px 9px;font-family:Rajdhani;color:#7a93b0;font-size:.75rem;">'
            f'{r["team_emoji"]} {r["team"]}</td>'
            f'<td style="padding:6px 9px;font-family:Rajdhani;font-weight:700;color:#e2e8f0;">'
            f'{r["port_emoji"]} {r["port"]}</td>'
            f'<td style="padding:6px 9px;font-family:Share Tech Mono;font-size:.68rem;color:#7a93b0;">'
            f'{r["strategy"]}</td>'
            f'<td style="padding:6px 9px;font-family:Share Tech Mono;">${r["total"]:,.0f}</td>'
            f'<td style="padding:6px 9px;color:{c_};font-family:Share Tech Mono;">'
            f'{sgn}${abs(r["pnl"]):,.0f}</td>'
            f'<td style="padding:6px 9px;color:{c_};font-weight:bold;">'
            f'{arr} {abs(r["pct"]):.2f}%</td>'
            f'<td style="padding:6px 9px;font-family:Share Tech Mono;color:#7a93b0;">${r["cash"]:,.0f}</td>'
            f'<td style="padding:6px 9px;color:#7a93b0;text-align:center;">{r["n_positions"]}</td>'
            f'<td style="padding:6px 9px;color:#7a93b0;text-align:center;">{r["n_trades"]}</td>'
            f'</tr>'
        )
    st.markdown(
        f'<div class="mam-table-wrap"><table class="mam-table">'
        f'<thead><tr>{th}</tr></thead><tbody>{tbody}</tbody></table></div>',
        unsafe_allow_html=True,
    )


# ── Portfolio view ────────────────────────────────────────────────────────────
def _portfolio_view(team, team_id, port, port_id, prices_dict, state):
    section_title(
        f'{port.get("emoji","💼")} {port["name"]} — {team.get("emoji","")} {team["name"]}', "📊")

    val   = value_portfolio(port, prices_dict)
    total = val["total"]
    cash  = val["cash"]
    init  = float(port.get("initial_cash", 1_000_000))
    pnl   = total - init
    pct   = pnl / init * 100 if init else 0

    history = port.get("history", [])
    now_str = datetime.now().isoformat()
    if not history or history[-1].get("date", "")[:10] != now_str[:10]:
        history.append({"date": now_str, "value": total})
        state["teams"][team_id]["portfolios"][port_id]["history"] = history[-365:]
        persist()

    metric_row([
        {"label": "Valeur totale",   "value": f"${total:,.2f}", "color": ""},
        {"label": "Cash disponible", "value": f"${cash:,.2f}",  "color": ""},
        {"label": "P&L Total",       "value": f"${pnl:+,.2f}",
         "color": "positive" if pnl >= 0 else "negative"},
        {"label": "Rendement",       "value": f"{pct:+.2f}%",
         "color": "positive" if pct >= 0 else "negative"},
        {"label": "Stratégie",       "value": port.get("strategy", "Libre"), "color": ""},
    ])
    st.markdown("<br>", unsafe_allow_html=True)

    tab_hold, tab_nav, tab_risk = st.tabs([
        "💼 POSITIONS", "📈 NAV & PERFORMANCE", "⚠️ RISQUE"])

    with tab_hold:
        _holdings_tab(val, prices_dict)
    with tab_nav:
        _nav_tab(history, total, init)
    with tab_risk:
        _risk_tab(history)


# ── Holdings tab ──────────────────────────────────────────────────────────────
def _holdings_tab(val: dict, prices_dict: dict):
    positions = val.get("positions", [])
    cash      = val.get("cash", 0.0)

    if not positions:
        st.info("📭 Aucune position. Tradez depuis le Trading Desk.")
        st.markdown(
            f'<div style="font-family:Share Tech Mono;font-size:.8rem;color:#7a93b0;margin-top:8px;">'
            f'Cash disponible : <b style="color:#00d4ff;">${cash:,.2f}</b></div>',
            unsafe_allow_html=True)
        return

    # ── Recalcul P&L factuel depuis prix live ─────────────────────────────────
    # value_portfolio stocke current_price (= prix live passé via prices_dict)
    # et avg_price (= prix d'achat). On s'assure d'utiliser ces deux valeurs.
    enriched = []
    for pos in positions:
        ticker     = pos["ticker"]
        qty        = float(pos.get("qty", 0))
        avg_price  = float(pos.get("avg_price", 0))
        # current_price vient de value_portfolio qui l'a résolu depuis prices_dict
        live_price = float(pos.get("current_price", avg_price))
        # Guard NaN
        if live_price != live_price or live_price <= 0:
            live_price = avg_price
        mkt_val    = qty * live_price
        unrealized = (live_price - avg_price) * qty
        pnl_pct    = (live_price - avg_price) / avg_price * 100 if avg_price else 0.0
        enriched.append({
            "ticker": ticker, "qty": qty,
            "avg_price": avg_price, "live_price": live_price,
            "mkt_val": mkt_val, "unrealized": unrealized, "pnl_pct": pnl_pct,
        })

    total_mkt  = sum(e["mkt_val"]    for e in enriched)
    total_upnl = sum(e["unrealized"] for e in enriched)
    total_val  = total_mkt + cash

    metric_row([
        {"label": "Positions",        "value": str(len(enriched)), "color": ""},
        {"label": "Valeur marché",    "value": f"${total_mkt:,.2f}", "color": ""},
        {"label": "P&L non réalisé",  "value": f"${total_upnl:+,.2f}",
         "color": "positive" if total_upnl >= 0 else "negative"},
        {"label": "Cash",             "value": f"${cash:,.2f}", "color": ""},
    ])
    st.markdown("<br>", unsafe_allow_html=True)

    # Tableau positions
    hdr = ["Ticker", "Qté", "Prix achat", "Prix live", "Valeur marché", "P&L ($)", "P&L (%)", "Poids"]
    th  = "".join(
        f'<th style="font-family:Rajdhani;font-size:.60rem;color:#00d4ff;letter-spacing:.08em;'
        f'text-transform:uppercase;padding:7px 9px;background:rgba(0,212,255,.06);'
        f'border-bottom:1px solid rgba(0,212,255,.18);">{c}</th>' for c in hdr)

    tbody = ""
    for e in sorted(enriched, key=lambda x: x["mkt_val"], reverse=True):
        c_  = "#00ff88" if e["unrealized"] >= 0 else "#ff3b6b"
        arr = "▲" if e["unrealized"] > 0 else ("▼" if e["unrealized"] < 0 else "─")
        sgn = "+" if e["unrealized"] >= 0 else ""
        w   = e["mkt_val"] / total_val * 100 if total_val else 0
        tbody += (
            f'<tr style="border-bottom:1px solid rgba(255,255,255,.04);">'
            f'<td style="padding:7px 9px;font-family:Rajdhani;font-size:.95rem;'
            f'font-weight:700;color:#00d4ff;">{e["ticker"]}</td>'
            f'<td style="padding:7px 9px;font-family:Share Tech Mono;">{e["qty"]:,.4f}</td>'
            f'<td style="padding:7px 9px;font-family:Share Tech Mono;color:#7a93b0;">'
            f'${e["avg_price"]:,.4f}</td>'
            f'<td style="padding:7px 9px;font-family:Share Tech Mono;color:#e2e8f0;">'
            f'${e["live_price"]:,.4f}</td>'
            f'<td style="padding:7px 9px;font-family:Share Tech Mono;">${e["mkt_val"]:,.2f}</td>'
            f'<td style="padding:7px 9px;font-family:Share Tech Mono;color:{c_};">'
            f'{sgn}${abs(e["unrealized"]):,.2f}</td>'
            f'<td style="padding:7px 9px;font-weight:bold;color:{c_};">'
            f'{arr} {abs(e["pnl_pct"]):.2f}%</td>'
            f'<td style="padding:7px 9px;">'
            f'<div style="background:rgba(0,212,255,.12);border-radius:3px;height:5px;overflow:hidden;">'
            f'<div style="width:{min(w,100):.0f}%;height:100%;background:rgba(0,212,255,.65);"></div></div>'
            f'<span style="font-family:Share Tech Mono;font-size:.63rem;color:#7a93b0;">{w:.1f}%</span>'
            f'</td></tr>'
        )
    st.markdown(
        f'<div class="mam-table-wrap"><table class="mam-table">'
        f'<thead><tr>{th}</tr></thead><tbody>{tbody}</tbody></table></div>',
        unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    section_title("RÉPARTITION", "🥧")
    labels = [e["ticker"] for e in enriched] + ["Cash"]
    values = [e["mkt_val"] for e in enriched] + [cash]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        textfont=dict(family="Share Tech Mono", size=10),
        marker=dict(colors=px.colors.qualitative.Dark24),
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f} (%{percent})<extra></extra>",
    ))
    fig.update_layout(**_P, height=280, showlegend=True,
        legend=dict(font=dict(size=9, family="Share Tech Mono"), bgcolor="rgba(0,0,0,0)"))
    st.plotly_chart(fig, use_container_width=True)


# ── NAV tab ───────────────────────────────────────────────────────────────────
def _nav_tab(history, current_total, init):
    section_title("NAV HISTORIQUE", "📈")
    if len(history) < 2:
        st.info("L'historique s'enrichit à chaque visite.")
        pnl  = current_total - init
        pct  = pnl / init * 100 if init else 0
        col_ = "#00ff88" if pnl >= 0 else "#ff3b6b"
        sgn  = "+" if pnl >= 0 else ""
        st.markdown(
            f'<div style="background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.2);'
            f'border-radius:10px;padding:20px;text-align:center;margin-top:12px;">'
            f'<div style="font-family:Rajdhani;font-size:.72rem;color:#7a93b0;">VALEUR ACTUELLE</div>'
            f'<div style="font-family:Share Tech Mono;font-size:2rem;color:#e2e8f0;">${current_total:,.2f}</div>'
            f'<div style="font-family:Share Tech Mono;font-size:1rem;color:{col_};">'
            f'{sgn}${abs(pnl):,.2f} ({sgn}{abs(pct):.2f}%)</div>'
            f'</div>', unsafe_allow_html=True)
        return

    df = pd.DataFrame(history)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates("date")
    df["pct"] = (df["value"] / init - 1) * 100

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.7, 0.3], vertical_spacing=0.04)
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["value"], mode="lines+markers",
        marker=dict(size=4), line=dict(color="#00d4ff", width=2.5),
        fill="tozeroy", fillcolor="rgba(0,212,255,.06)", name="NAV",
    ), row=1, col=1)
    fig.add_hline(y=init, line_color="rgba(255,215,0,.4)", line_dash="dot",
                  annotation_text=f"Capital ${init:,.0f}",
                  annotation_font_color="#ffd700", row=1, col=1)
    fig.add_trace(go.Bar(
        x=df["date"], y=df["pct"], name="Rend. (%)",
        marker_color=["rgba(0,255,136,.6)" if v >= 0 else "rgba(255,59,107,.6)"
                      for v in df["pct"]],
    ), row=2, col=1)
    fig.update_layout(**_P, height=380,
        yaxis=dict(title="Valeur ($)", gridcolor="rgba(255,255,255,.04)"),
        yaxis2=dict(title="Rend. (%)", gridcolor="rgba(255,255,255,.04)"))
    st.plotly_chart(fig, use_container_width=True)


# ── Risk tab ──────────────────────────────────────────────────────────────────
def _risk_tab(history):
    section_title("MÉTRIQUES DE RISQUE", "⚠️")
    if len(history) < 5:
        st.info("Min. 5 observations nécessaires.")
        return
    df      = pd.DataFrame(history).sort_values("date")
    returns = df["value"].pct_change().dropna()
    m       = compute_risk_metrics(returns)
    if not m:
        st.warning("Calcul impossible.")
        return
    metric_row([
        {"label": "Sharpe",    "value": f'{m.get("sharpe",0):.3f}',
         "color": "positive" if m.get("sharpe",0) >= 1 else "neutral"},
        {"label": "Sortino",   "value": f'{m.get("sortino",0):.3f}',
         "color": "positive" if m.get("sortino",0) >= 1 else "neutral"},
        {"label": "Max DD",    "value": f'{m.get("max_drawdown",0)*100:.2f}%', "color": "negative"},
        {"label": "Vol. ann.", "value": f'{m.get("ann_vol",0)*100:.2f}%', "color": ""},
        {"label": "VaR 99%",   "value": f'{m.get("var_99_10d",0)*100:.2f}%', "color": "negative"},
        {"label": "CVaR 99%",  "value": f'{m.get("cvar_99_10d",0)*100:.2f}%', "color": "negative"},
    ])
