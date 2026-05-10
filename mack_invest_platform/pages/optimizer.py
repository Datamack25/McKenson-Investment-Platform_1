# pages/leaderboard.py  —  MAM Leaderboard
"""
Real-time leaderboard — team and portfolio rankings by P&L, Sharpe, returns.
Podium display, performance charts, and statistics.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from datetime import datetime

from components.ui import section_title, metric_row
from utils.data import get_or_init_state, get_multi_prices, value_portfolio, compute_risk_metrics

_P = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
          font=dict(color="#94a3b8", family="Share Tech Mono"),
          margin=dict(l=8, r=8, t=28, b=8))


def render():
    st.markdown(
        '<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;letter-spacing:.12em;'
        'color:#ffd700;margin:0 0 2px;text-shadow:0 0 30px rgba(255,215,0,.4);">'
        '🏆 LEADERBOARD — MAM</h1>', unsafe_allow_html=True)

    state  = get_or_init_state()
    teams  = state.get("teams", {})

    if not teams:
        st.info("Aucune équipe enregistrée.")
        return

    # Pre-fetch all prices
    all_tickers: set[str] = set()
    for t in teams.values():
        for p in t["portfolios"].values():
            all_tickers.update(p.get("holdings", {}).keys())

    with st.spinner("⏳ Actualisation des prix..."):
        prices_raw = get_multi_prices(tuple(all_tickers))
    prices = {t: prices_raw[t][0] for t in prices_raw}

    # Compute all portfolio stats
    all_ports = []
    team_agg   = {}

    for tid, team in teams.items():
        team_total = 0.0
        team_init  = 0.0
        team_trades = 0

        for pid, port in team["portfolios"].items():
            val   = value_portfolio(port, prices)
            total = val["total"]
            init  = port.get("initial_cash", 1_000_000)
            pnl   = total - init
            pct   = pnl / init * 100 if init else 0
            n_tr  = len(port.get("trades", []))
            n_pos = len(val["positions"])

            # Risk metrics from history
            hist  = port.get("history", [])
            sharpe, mdd, ann_vol = 0.0, 0.0, 0.0
            if len(hist) >= 5:
                hdf  = pd.DataFrame(hist)
                rets = hdf["value"].pct_change().dropna()
                m    = compute_risk_metrics(rets)
                if m:
                    sharpe  = m["sharpe"]
                    mdd     = m["max_drawdown"]
                    ann_vol = m["ann_vol"]

            all_ports.append({
                "team_id": tid, "team":  team["name"], "team_emoji": team["emoji"],
                "port_id": pid, "port":  port["name"], "port_emoji": port["emoji"],
                "strategy": port.get("strategy", ""),
                "total": total, "init": init,
                "pnl": pnl, "pct": pct,
                "n_positions": n_pos, "n_trades": n_tr,
                "sharpe": sharpe, "max_drawdown": mdd, "ann_vol": ann_vol,
            })

            team_total  += total
            team_init   += init
            team_trades += n_tr

        team_pnl  = team_total - team_init
        team_pct  = team_pnl / team_init * 100 if team_init else 0
        team_agg[tid] = {
            "team": team["name"], "emoji": team["emoji"],
            "total": team_total, "init": team_init,
            "pnl": team_pnl, "pct": team_pct,
            "n_trades": team_trades,
            "n_ports": len(team["portfolios"]),
        }

    tab_teams, tab_ports, tab_strategy = st.tabs([
        "🏆 CLASSEMENT ÉQUIPES",
        "📊 CLASSEMENT PORTEFEUILLES",
        "🎯 PAR STRATÉGIE",
    ])

    with tab_teams:
        _teams_ranking(team_agg)

    with tab_ports:
        _portfolios_ranking(all_ports)

    with tab_strategy:
        _strategy_ranking(all_ports)


# ─────────────────────────────────────────────────────────────────────────────
def _teams_ranking(team_agg):
    section_title("CLASSEMENT GÉNÉRAL — ÉQUIPES", "🏆")

    sorted_teams = sorted(team_agg.values(), key=lambda x: x["pct"], reverse=True)

    # Podium (top 3)
    if len(sorted_teams) >= 1:
        st.markdown('<div style="display:flex;justify-content:center;gap:16px;margin:16px 0 24px;flex-wrap:wrap;">',
                    unsafe_allow_html=True)

        medals = ["🥇", "🥈", "🥉"]
        heights = ["160px", "130px", "110px"]
        order   = [1, 0, 2] if len(sorted_teams) >= 3 else list(range(len(sorted_teams)))

        pods = ""
        for rank_idx in order:
            if rank_idx >= len(sorted_teams):
                continue
            t = sorted_teams[rank_idx]
            medal = medals[rank_idx] if rank_idx < 3 else f"#{rank_idx+1}"
            pnl_col = "#00ff88" if t["pnl"] >= 0 else "#ff3b6b"
            sign    = "+" if t["pnl"] >= 0 else ""
            pods += (
                f'<div style="background:rgba(0,212,255,.06);border:1px solid rgba(0,212,255,.2);'
                f'border-radius:12px;padding:16px 20px;text-align:center;min-width:160px;'
                f'box-shadow:0 0 20px rgba(0,212,255,.12);">'
                f'<div style="font-size:1.8rem;">{medal}</div>'
                f'<div style="font-size:1.6rem;">{t["emoji"]}</div>'
                f'<div style="font-family:Rajdhani;font-size:1.1rem;font-weight:700;'
                f'color:#e2e8f0;letter-spacing:.05em;">{t["team"]}</div>'
                f'<div style="font-family:Share Tech Mono;font-size:1.3rem;color:{pnl_col};'
                f'font-weight:bold;margin-top:6px;">{sign}{t["pct"]:.2f}%</div>'
                f'<div style="font-family:Share Tech Mono;font-size:.75rem;color:#7a93b0;">'
                f'${t["total"]:,.0f}</div>'
                f'<div style="font-family:Share Tech Mono;font-size:.7rem;color:#7a93b0;margin-top:4px;">'
                f'{t["n_trades"]} trades</div>'
                f'</div>'
            )
        st.markdown(pods + '</div>', unsafe_allow_html=True)

    # Full table
    hdr_cols = ["Rang", "Équipe", "Capital total", "P&L ($)", "P&L (%)", "Trades", "Portefeuilles"]
    th = "".join(
        f'<th style="font-family:Rajdhani;font-size:.67rem;color:#ffd700;'
        f'letter-spacing:.1em;text-transform:uppercase;padding:8px 10px;'
        f'background:rgba(255,215,0,.06);border-bottom:1px solid rgba(255,215,0,.18);">'
        f'{c}</th>' for c in hdr_cols)

    tbody = ""
    for rank, t in enumerate(sorted_teams, 1):
        pnl_cls = "pnl-pos" if t["pnl"] > 0 else ("pnl-neg" if t["pnl"] < 0 else "pnl-zero")
        sign    = "+" if t["pnl"] > 0 else ""
        arr     = "▲" if t["pnl"] > 0 else ("▼" if t["pnl"] < 0 else "▬")
        medal   = ["🥇", "🥈", "🥉"][rank-1] if rank <= 3 else f"#{rank}"
        tbody += (
            f'<tr style="border-bottom:1px solid rgba(255,255,255,.04);">'
            f'<td style="padding:7px 14px;font-size:1.1rem;text-align:center;">{medal}</td>'
            f'<td style="padding:7px 10px;font-family:Rajdhani;font-size:.95rem;'
            f'font-weight:700;color:#e2e8f0;">{t["emoji"]} {t["team"]}</td>'
            f'<td style="padding:7px 10px;font-family:Share Tech Mono;color:#e2e8f0;">${t["total"]:,.0f}</td>'
            f'<td style="padding:7px 10px;" class="{pnl_cls}">{sign}${abs(t["pnl"]):,.0f}</td>'
            f'<td style="padding:7px 10px;" class="{pnl_cls}">{arr} {sign}{abs(t["pct"]):.2f}%</td>'
            f'<td style="padding:7px 10px;color:#7a93b0;">{t["n_trades"]}</td>'
            f'<td style="padding:7px 10px;color:#7a93b0;">{t["n_ports"]}</td>'
            f'</tr>'
        )

    st.markdown(
        f'<div class="mam-table-wrap"><table class="mam-table">'
        f'<thead><tr>{th}</tr></thead><tbody>{tbody}</tbody></table></div>',
        unsafe_allow_html=True)

    # Bar chart
    st.markdown("<br>", unsafe_allow_html=True)
    section_title("P&L PAR ÉQUIPE", "📊")
    fig = go.Figure(go.Bar(
        x=[t["team"] for t in sorted_teams],
        y=[t["pct"] for t in sorted_teams],
        marker_color=["rgba(0,255,136,.7)" if t["pct"] >= 0 else "rgba(255,59,107,.7)"
                      for t in sorted_teams],
        text=[f'{"+" if t["pct"]>=0 else ""}{t["pct"]:.2f}%' for t in sorted_teams],
        textposition="outside",
        hovertemplate="%{x}<br>P&L: %{y:+.2f}%<extra></extra>"))
    fig.add_hline(y=0, line_color="rgba(255,255,255,.2)")
    fig.update_layout(**_P, height=250,
        xaxis=dict(showgrid=False),
        yaxis=dict(title="P&L (%)", gridcolor="rgba(255,255,255,.04)"))
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
def _portfolios_ranking(all_ports):
    section_title("CLASSEMENT TOUS PORTEFEUILLES", "📊")

    sort_by = st.radio("Trier par", ["P&L (%)", "P&L ($)", "Sharpe", "# Trades"],
                        horizontal=True, key="lb_sort")

    sort_map = {
        "P&L (%)": "pct", "P&L ($)": "pnl",
        "Sharpe": "sharpe", "# Trades": "n_trades"
    }
    key = sort_map[sort_by]
    sorted_ports = sorted(all_ports, key=lambda x: x[key], reverse=True)

    hdr_cols = ["Rang", "Équipe", "Portefeuille", "Stratégie", "Valeur",
                "P&L ($)", "P&L (%)", "Sharpe", "Max DD", "Trades"]
    th = "".join(
        f'<th style="font-family:Rajdhani;font-size:.62rem;color:#00d4ff;'
        f'letter-spacing:.08em;text-transform:uppercase;padding:7px 8px;'
        f'background:rgba(0,212,255,.06);border-bottom:1px solid rgba(0,212,255,.18);">'
        f'{c}</th>' for c in hdr_cols)

    tbody = ""
    for rank, p in enumerate(sorted_ports, 1):
        pnl_cls = "pnl-pos" if p["pnl"] > 0 else ("pnl-neg" if p["pnl"] < 0 else "pnl-zero")
        sign    = "+" if p["pnl"] > 0 else ""
        arr     = "▲" if p["pnl"] > 0 else ("▼" if p["pnl"] < 0 else "▬")
        medal   = ["🥇", "🥈", "🥉"][rank-1] if rank <= 3 else f"{rank}"
        sh_col  = "#00ff88" if p["sharpe"] >= 1 else ("#ffd700" if p["sharpe"] >= 0 else "#ff3b6b")
        tbody += (
            f'<tr style="border-bottom:1px solid rgba(255,255,255,.04);">'
            f'<td style="padding:6px 10px;font-size:.95rem;text-align:center;">{medal}</td>'
            f'<td style="padding:6px 8px;color:#7a93b0;font-size:.75rem;">'
            f'{p["team_emoji"]} {p["team"]}</td>'
            f'<td style="padding:6px 8px;font-family:Rajdhani;font-weight:700;color:#e2e8f0;">'
            f'{p["port_emoji"]} {p["port"]}</td>'
            f'<td style="padding:6px 8px;font-family:Share Tech Mono;font-size:.7rem;color:#7a93b0;">'
            f'{p["strategy"]}</td>'
            f'<td style="padding:6px 8px;font-family:Share Tech Mono;font-size:.78rem;">'
            f'${p["total"]:,.0f}</td>'
            f'<td style="padding:6px 8px;" class="{pnl_cls}">{sign}${abs(p["pnl"]):,.0f}</td>'
            f'<td style="padding:6px 8px;" class="{pnl_cls}">{arr} {abs(p["pct"]):.2f}%</td>'
            f'<td style="padding:6px 8px;color:{sh_col};font-family:Share Tech Mono;">'
            f'{p["sharpe"]:.2f}</td>'
            f'<td style="padding:6px 8px;color:#ff3b6b;font-family:Share Tech Mono;">'
            f'{p["max_drawdown"]*100:.1f}%</td>'
            f'<td style="padding:6px 8px;color:#7a93b0;">{p["n_trades"]}</td>'
            f'</tr>'
        )

    st.markdown(
        f'<div class="mam-table-wrap"><table class="mam-table">'
        f'<thead><tr>{th}</tr></thead><tbody>{tbody}</tbody></table></div>',
        unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
def _strategy_ranking(all_ports):
    section_title("PERFORMANCE PAR STRATÉGIE", "🎯")

    if not all_ports:
        st.info("Aucune donnée disponible.")
        return

    strat_perf = {}
    for p in all_ports:
        s = p.get("strategy", "unknown")
        if s not in strat_perf:
            strat_perf[s] = {"pnl": [], "pct": [], "name": p["port"], "emoji": p["port_emoji"]}
        strat_perf[s]["pnl"].append(p["pnl"])
        strat_perf[s]["pct"].append(p["pct"])

    rows = []
    for s, data in strat_perf.items():
        rows.append({
            "Stratégie": f'{data["emoji"]} {data["name"]}',
            "P&L moyen": np.mean(data["pnl"]),
            "P&L % moyen": np.mean(data["pct"]),
            "Meilleur": max(data["pct"]),
            "Pire": min(data["pct"]),
            "Nb portefeuilles": len(data["pct"]),
        })

    rows.sort(key=lambda x: x["P&L % moyen"], reverse=True)

    # Chart
    fig = go.Figure()
    strats  = [r["Stratégie"] for r in rows]
    means   = [r["P&L % moyen"] for r in rows]
    bests   = [r["Meilleur"] for r in rows]
    worsts  = [r["Pire"] for r in rows]

    fig.add_trace(go.Bar(
        x=strats, y=means,
        name="P&L moyen (%)",
        marker_color=["rgba(0,255,136,.7)" if v >= 0 else "rgba(255,59,107,.7)" for v in means],
        text=[f'{"+" if v>=0 else ""}{v:.2f}%' for v in means],
        textposition="outside",
        hovertemplate="%{x}<br>Moyen: %{y:+.2f}%<extra></extra>"))

    fig.update_layout(**_P, height=300,
        xaxis=dict(showgrid=False, tickangle=-25),
        yaxis=dict(title="P&L moyen (%)", gridcolor="rgba(255,255,255,.04)"))
    st.plotly_chart(fig, use_container_width=True)

    # Table
    tbl = pd.DataFrame([{
        "Stratégie":     r["Stratégie"],
        "P&L moyen (%)": f'{r["P&L % moyen"]:+.2f}%',
        "P&L moyen ($)": f'${r["P&L moyen"]:+,.0f}',
        "Meilleur (%)":  f'{r["Meilleur"]:+.2f}%',
        "Pire (%)":      f'{r["Pire"]:+.2f}%',
        "# Portefeuilles": r["Nb portefeuilles"],
    } for r in rows])

    st.dataframe(tbl, use_container_width=True, hide_index=True)
