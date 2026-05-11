# pages/dashboard.py  —  MAM v4.0
"""
Dashboard : n'affiche que les portefeuilles créés par l'utilisateur.
P&L calculé en temps réel via yfinance (prix actuel vs prix moyen d'entrée).
Aucun tableau vide si aucun portefeuille n'existe.
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from components.ui import section_title
from utils.data import (
    get_or_init_state, load_assets,
    get_multi_prices, get_price_change,
)


def render():
    state   = get_or_init_state()
    team_id = st.session_state.get("active_team")
    teams   = state.get("teams", {})

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        '<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;letter-spacing:.12em;'
        'color:#00ff88;margin:0 0 2px;text-shadow:0 0 30px rgba(0,255,136,.4);">'
        '🏠 DASHBOARD — MAM</h1>',
        unsafe_allow_html=True,
    )

    if not team_id or team_id not in teams:
        st.info("👈 Sélectionnez ou créez une équipe dans la barre latérale.")
        _empty_state()
        return

    team  = teams[team_id]
    ports = team.get("portfolios", {})

    # ── Filtrer uniquement les portefeuilles créés (avec un nom) ─────────────
    user_ports = {
        pid: p for pid, p in ports.items()
        if p.get("name") and p.get("name") != ""
    }

    if not user_ports:
        st.info("Aucun portefeuille constitué. Rendez-vous dans l'onglet **Portfolios** pour en créer un.")
        _empty_state()
        return

    # ── KPIs globaux ──────────────────────────────────────────────────────────
    total_cash    = 0.0
    total_mkt     = 0.0
    total_pnl     = 0.0
    total_cost    = 0.0
    total_ports   = len(user_ports)
    ports_with_pos = 0

    port_summaries = []

    for pid, port in user_ports.items():
        holdings = port.get("holdings", {})
        cash     = port.get("cash", 0.0)
        total_cash += cash

        if not holdings:
            port_summaries.append({
                "pid": pid, "port": port,
                "mkt_value": 0.0, "pnl": 0.0, "cost": 0.0,
                "positions": [],
            })
            continue

        ports_with_pos += 1
        tickers = tuple(holdings.keys())
        prices  = get_multi_prices(tickers)

        mkt  = 0.0
        cost = 0.0
        pnl  = 0.0
        positions = []

        for tk, pos in holdings.items():
            qty = pos.get("qty", 0)
            avg = pos.get("avg_price", 0.0)
            curr, pct_d = prices.get(tk, (avg, 0.0))
            pos_mkt  = qty * curr
            pos_cost = qty * avg
            pos_pnl  = pos_mkt - pos_cost
            mkt  += pos_mkt
            cost += pos_cost
            pnl  += pos_pnl
            positions.append({
                "ticker": tk, "qty": qty, "avg": avg,
                "curr": curr, "pct_d": pct_d,
                "mkt": pos_mkt, "cost": pos_cost, "pnl": pos_pnl,
            })

        total_mkt  += mkt
        total_cost += cost
        total_pnl  += pnl

        port_summaries.append({
            "pid": pid, "port": port,
            "mkt_value": mkt, "pnl": pnl, "cost": cost,
            "positions": positions,
        })

    total_aum      = total_cash + total_mkt
    total_pnl_pct  = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0

    # ── KPI Cards ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    kpi_style = (
        'background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.15);'
        'border-radius:8px;padding:14px 16px;'
    )
    pnl_col = "#00ff88" if total_pnl >= 0 else "#ff3b6b"

    with c1:
        st.markdown(
            f'<div style="{kpi_style}">'
            f'<div style="font-family:Rajdhani;font-size:.68rem;color:#7a93b0;'
            f'letter-spacing:.12em;text-transform:uppercase;">AUM Total</div>'
            f'<div style="font-family:Share Tech Mono;font-size:1.5rem;color:#e2e8f0;">'
            f'${total_aum:,.0f}</div>'
            f'<div style="font-size:.7rem;color:#475569;">{total_ports} portefeuille(s)</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div style="{kpi_style}">'
            f'<div style="font-family:Rajdhani;font-size:.68rem;color:#7a93b0;'
            f'letter-spacing:.12em;text-transform:uppercase;">Cash Total</div>'
            f'<div style="font-family:Share Tech Mono;font-size:1.5rem;color:#00d4ff;">'
            f'${total_cash:,.0f}</div>'
            f'<div style="font-size:.7rem;color:#475569;">'
            f'{total_cash/total_aum*100:.1f}% du portefeuille' if total_aum > 0 else "—"
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div style="{kpi_style}">'
            f'<div style="font-family:Rajdhani;font-size:.68rem;color:#7a93b0;'
            f'letter-spacing:.12em;text-transform:uppercase;">Valeur Marché</div>'
            f'<div style="font-family:Share Tech Mono;font-size:1.5rem;color:#e2e8f0;">'
            f'${total_mkt:,.0f}</div>'
            f'<div style="font-size:.7rem;color:#475569;">{ports_with_pos} portefeuille(s) en position</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c4:
        sg = "+" if total_pnl >= 0 else ""
        st.markdown(
            f'<div style="{kpi_style}">'
            f'<div style="font-family:Rajdhani;font-size:.68rem;color:#7a93b0;'
            f'letter-spacing:.12em;text-transform:uppercase;">P&L Global</div>'
            f'<div style="font-family:Share Tech Mono;font-size:1.5rem;color:{pnl_col};">'
            f'{sg}${abs(total_pnl):,.2f}</div>'
            f'<div style="font-size:.7rem;color:{pnl_col};">{sg}{abs(total_pnl_pct):.2f}%</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Portefeuilles créés ────────────────────────────────────────────────────
    section_title("MES PORTEFEUILLES", "📁")

    for summary in port_summaries:
        port     = summary["port"]
        pid      = summary["pid"]
        mkt_val  = summary["mkt_value"]
        pnl      = summary["pnl"]
        cost     = summary["cost"]
        positions = summary["positions"]
        cash     = port.get("cash", 0.0)
        port_type = port.get("portfolio_type", "Libre")
        ppct     = (pnl / cost * 100) if cost > 0 else 0.0

        p_col = "#00ff88" if pnl >= 0 else "#ff3b6b"
        sg    = "+" if pnl >= 0 else ""
        emoji = port.get("emoji", "📁")
        name  = port.get("name", "—")

        # ── Card header ───────────────────────────────────────────────────────
        st.markdown(
            f'<div style="background:rgba(0,10,25,.6);border:1px solid rgba(0,212,255,.18);'
            f'border-radius:10px;padding:16px 20px;margin-bottom:8px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'margin-bottom:12px;">'
            f'<div>'
            f'<span style="font-family:Rajdhani;font-size:1.1rem;font-weight:700;'
            f'color:#e2e8f0;">{emoji} {name}</span>'
            f'<span style="font-family:Rajdhani;font-size:.68rem;color:#475569;'
            f'letter-spacing:.12em;text-transform:uppercase;margin-left:10px;">{port_type}</span>'
            f'</div>'
            f'<div style="text-align:right;">'
            f'<div style="font-family:Share Tech Mono;font-size:.82rem;color:#e2e8f0;">'
            f'AUM <b>${cash + mkt_val:,.0f}</b></div>'
            f'<div style="font-family:Share Tech Mono;font-size:.78rem;color:{p_col};">'
            f'P&L {sg}${abs(pnl):,.2f} ({sg}{abs(ppct):.2f}%)</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # ── Positions de ce portefeuille (uniquement si > 0 positions) ───────
        if positions:
            hdr = ["Ticker", "Qté", "Px entrée", "Px actuel", "Var. 1j", "Valeur", "P&L $", "P&L %"]
            th  = "".join(
                f'<th style="font-family:Rajdhani;font-size:.63rem;color:#00d4ff;'
                f'letter-spacing:.08em;text-transform:uppercase;padding:5px 8px;'
                f'background:rgba(0,212,255,.05);border-bottom:1px solid rgba(0,212,255,.12);">'
                f'{c}</th>' for c in hdr
            )
            tbody = ""
            for pos in positions:
                tk   = pos["ticker"]
                qty  = pos["qty"]
                avg  = pos["avg"]
                curr = pos["curr"]
                pd_  = pos["pct_d"]
                p_v  = pos["mkt"]
                p_pnl = pos["pnl"]
                p_cost = pos["cost"]
                p_pct = (p_pnl / p_cost * 100) if p_cost > 0 else 0.0

                pc   = "#00ff88" if p_pnl > 0 else ("#ff3b6b" if p_pnl < 0 else "#94a3b8")
                dc   = "#00ff88" if pd_ > 0 else ("#ff3b6b" if pd_ < 0 else "#94a3b8")
                sg_p = "+" if p_pnl > 0 else ""
                ar   = "▲" if p_pnl > 0 else ("▼" if p_pnl < 0 else "▬")
                dr   = "▲" if pd_ > 0 else ("▼" if pd_ < 0 else "▬")

                tbody += (
                    f'<tr style="border-bottom:1px solid rgba(255,255,255,.03);">'
                    f'<td style="padding:5px 8px;color:#00d4ff;font-weight:bold;">{tk}</td>'
                    f'<td style="padding:5px 8px;">{qty:,.4f}</td>'
                    f'<td style="padding:5px 8px;color:#7a93b0;">${avg:,.4f}</td>'
                    f'<td style="padding:5px 8px;">${curr:,.4f}</td>'
                    f'<td style="padding:5px 8px;color:{dc};">{dr} {abs(pd_):.2f}%</td>'
                    f'<td style="padding:5px 8px;">${p_v:,.2f}</td>'
                    f'<td style="padding:5px 8px;color:{pc};font-weight:bold;">{sg_p}${abs(p_pnl):,.2f}</td>'
                    f'<td style="padding:5px 8px;color:{pc};">{ar} {abs(p_pct):.2f}%</td>'
                    f'</tr>'
                )

            st.markdown(
                f'<div style="overflow-x:auto;margin-top:4px;">'
                f'<table style="width:100%;border-collapse:collapse;font-family:Share Tech Mono;'
                f'font-size:.74rem;color:#e2e8f0;">'
                f'<thead><tr>{th}</tr></thead><tbody>{tbody}</tbody></table></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="font-family:Share Tech Mono;font-size:.74rem;color:#475569;'
                f'padding:6px 0;">Aucune position — Cash disponible : '
                f'<span style="color:#00d4ff;">${cash:,.2f}</span></div>',
                unsafe_allow_html=True,
            )

        # Fermer la card div
        st.markdown('</div>', unsafe_allow_html=True)


def _empty_state():
    """Affichage si aucun portefeuille."""
    st.markdown(
        '<div style="text-align:center;padding:60px 0;color:#334155;">'
        '<div style="font-size:3rem;margin-bottom:16px;">📁</div>'
        '<div style="font-family:Rajdhani;font-size:1.1rem;letter-spacing:.12em;'
        'text-transform:uppercase;color:#475569;">Aucun portefeuille constitué</div>'
        '<div style="font-family:Share Tech Mono;font-size:.75rem;color:#334155;'
        'margin-top:8px;">Créez un portefeuille dans l\'onglet Portfolios</div>'
        '</div>',
        unsafe_allow_html=True,
    )
