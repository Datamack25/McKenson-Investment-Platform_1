# pages/dashboard.py  —  MAM Dashboard
"""
Multi-portfolio dashboard: global P&L, MWR/TWR performance,
holdings breakdown, historical NAV, risk metrics per portfolio.
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

_P = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
          font=dict(color="#94a3b8", family="Share Tech Mono"),
          margin=dict(l=8, r=8, t=28, b=8))


def render():
    # ── FIX 2 : bandeau abaissé via margin-top ────────────────────────────────
    st.markdown(
        '<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;letter-spacing:.12em;'
        'color:#00d4ff;margin:48px 0 2px;text-shadow:0 0 30px rgba(0,212,255,.4);">'
        '🏠 DASHBOARD — MAM</h1>', unsafe_allow_html=True)

    state   = get_or_init_state()
    teams   = state.get("teams", {})
    team_id = st.session_state.get("active_team")
    port_id = st.session_state.get("active_portfolio")

    if not teams:
        _no_teams_placeholder()
        return

    # Pre-fetch all prices once
    all_tickers: set[str] = set()
    for t in teams.values():
        for p in t["portfolios"].values():
            all_tickers.update(p.get("holdings", {}).keys())

    with st.spinner("⏳ Mise à jour des prix…"):
        prices_raw = get_multi_prices(tuple(all_tickers)) if all_tickers else {}
    prices_dict = {t: v[0] for t, v in prices_raw.items()}

    # ── View selector ──────────────────────────────────────────────────────────
    view = st.radio(
        "Vue", ["🌐 Vue globale", "📊 Portefeuille actif"],
        horizontal=True, key="dash_view")

    st.markdown("<br>", unsafe_allow_html=True)

    if view == "🌐 Vue globale":
        _global_view(teams, prices_dict)
    else:
        if not team_id or not port_id:
            st.warning("⚠️ Sélectionnez une équipe et un portefeuille dans la barre latérale.")
            _global_view(teams, prices_dict)
        else:
            port = teams[team_id]["portfolios"].get(port_id)
            team = teams[team_id]
            if port:
                _portfolio_view(team, team_id, port, port_id, prices_dict, state)
            else:
                st.error("Portefeuille introuvable.")


# ── No teams ──────────────────────────────────────────────────────────────────
def _no_teams_placeholder():
    st.markdown(
        '<div style="text-align:center;padding:60px 20px;">'
        '<div style="font-size:4rem;margin-bottom:16px;">🏦</div>'
        '<div style="font-family:Rajdhani;font-size:1.4rem;font-weight:700;'
        'color:#e2e8f0;letter-spacing:.1em;margin-bottom:10px;">BIENVENUE SUR MAM</div>'
        '<div style="font-family:Share Tech Mono;font-size:.8rem;color:#7a93b0;'
        'line-height:1.8;">McKenson Asset Management — Professional Investment Simulation<br>'
        'Créez des équipes dans le panneau Admin pour commencer.</div>'
        '</div>',
        unsafe_allow_html=True)


# ── Global view ───────────────────────────────────────────────────────────────
def _global_view(teams: dict, prices_dict: dict):
    section_title("VUE GLOBALE — TOUTES LES ÉQUIPES", "🌐")

    # ── FIX 3 : n'agréger QUE les portefeuilles réellement créés ──────────────
    # Un portefeuille est "réel" s'il a été créé explicitement (a un nom non vide)
    all_rows  = []
    team_agg  = []

    for tid, team in teams.items():
        team_total = 0.0
        team_init  = 0.0

        for pid, port in team["portfolios"].items():
            # Ignorer les portefeuilles vides / placeholders sans nom
            if not port.get("name", "").strip():
                continue

            val      = value_portfolio(port, prices_dict)
            total    = val["total"]
            init     = float(port.get("initial_cash", 1_000_000))
            pnl      = total - init
            pct      = pnl / init * 100 if init else 0
            n_trades = len(port.get("trades", []))
            n_pos    = len(val["positions"])

            all_rows.append({
                "team": team["name"], "team_emoji": team["emoji"],
                "port": port["name"], "port_emoji": port.get("emoji", "💼"),
                "strategy": port.get("strategy", ""),
                "total": total, "init": init,
                "pnl": pnl, "pct": pct,
                "n_trades": n_trades, "n_positions": n_pos,
                "cash": val["cash"],
            })
            team_total += total
            team_init  += init

        if team_total > 0 or team_init > 0:
            team_agg.append({
                "name": team["name"], "emoji": team["emoji"],
                "total": team_total, "pnl": team_total - team_init,
                "pct": (team_total - team_init) / team_init * 100 if team_init else 0,
            })

    # ── Top summary strip ──────────────────────────────────────────────────────
    total_aum    = sum(r["total"] for r in all_rows)
    total_pnl    = sum(r["pnl"]   for r in all_rows)
    total_init   = sum(r["init"]  for r in all_rows)
    total_pct    = total_pnl / total_init * 100 if total_init else 0
    n_profitable = sum(1 for r in all_rows if r["pnl"] > 0)

    metric_row([
        {"label": "AUM Total",         "value": f"${total_aum:,.0f}",  "color": ""},
        {"label": "P&L Total",         "value": f'${total_pnl:+,.0f}',
         "color": "positive" if total_pnl >= 0 else "negative"},
        {"label": "Rendement moyen",   "value": f"{total_pct:+.2f}%",
         "color": "positive" if total_pct >= 0 else "negative"},
        {"label": "Portefeuilles + / Total",
         "value": f"{n_profitable} / {len(all_rows)}", "color": ""},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Team leaderboard bar ───────────────────────────────────────────────────
    team_agg_sorted = sorted(team_agg, key=lambda x: x["pct"], reverse=True)

    col_chart, col_table = st.columns([3, 2])

    with col_chart:
        section_title("P&L PAR ÉQUIPE", "📊")
        if team_agg_sorted:
            fig = go.Figure(go.Bar(
                x=[f'{t["emoji"]} {t["name"]}' for t in team_agg_sorted],
                y=[t["pct"] for t in team_agg_sorted],
                marker_color=["rgba(0,255,136,.7)" if t["pct"] >= 0
                              else "rgba(255,59,107,.7)" for t in team_agg_sorted],
                text=[f'{"+" if t["pct"]>=0 else ""}{t["pct"]:.2f}%'
                      for t in team_agg_sorted],
                textposition="outside",
                hovertemplate="%{x}<br>P&L: %{y:+.2f}%<extra></extra>"))
            fig.add_hline(y=0, line_color="rgba(255,255,255,.2)")
            fig.update_layout(**_P, height=240,
                xaxis=dict(showgrid=False),
                yaxis=dict(title="P&L (%)", gridcolor="rgba(255,255,255,.04)"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucun portefeuille créé.")

    with col_table:
        section_title("CLASSEMENT", "🏆")
        for i, t in enumerate(team_agg_sorted):
            medal   = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
            pnl_col = "#00ff88" if t["pct"] >= 0 else "#ff3b6b"
            sign    = "+" if t["pct"] >= 0 else ""
            st.markdown(
                f'<div style="background:rgba(0,0,0,.2);border:1px solid rgba(255,255,255,.06);'
                f'border-radius:6px;padding:8px 12px;margin-bottom:6px;'
                f'display:flex;justify-content:space-between;align-items:center;">'
                f'<div style="font-family:Rajdhani;font-size:.9rem;font-weight:700;color:#e2e8f0;">'
                f'{medal} {t["emoji"]} {t["name"]}</div>'
                f'<div style="font-family:Share Tech Mono;font-size:.85rem;'
                f'color:{pnl_col};font-weight:bold;">{sign}{t["pct"]:.2f}%</div>'
                f'</div>',
                unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── All portfolios table (uniquement ceux réellement créés) ───────────────
    section_title("TOUS LES PORTEFEUILLES", "📋")

    if not all_rows:
        st.info("Aucun portefeuille créé pour le moment.")
    else:
        all_rows_sorted = sorted(all_rows, key=lambda x: x["pct"], reverse=True)

        hdr = ["#", "Équipe", "Portefeuille", "Stratégie",
               "Valeur", "P&L ($)", "P&L (%)", "Cash", "Positions", "Trades"]
        th = "".join(
            f'<th style="font-family:Rajdhani;font-size:.62rem;color:#00d4ff;'
            f'letter-spacing:.08em;text-transform:uppercase;padding:7px 9px;'
            f'background:rgba(0,212,255,.06);border-bottom:1px solid rgba(0,212,255,.18);">'
            f'{c}</th>' for c in hdr)

        tbody = ""
        for i, r in enumerate(all_rows_sorted, 1):
            pnl_col = "#00ff88" if r["pnl"] >= 0 else "#ff3b6b"
            sign    = "+" if r["pnl"] >= 0 else ""
            arr     = "▲" if r["pnl"] > 0 else "▼"
            medal   = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else str(i)
            tbody += (
                f'<tr style="border-bottom:1px solid rgba(255,255,255,.04);">'
                f'<td style="padding:6px 10px;text-align:center;">{medal}</td>'
                f'<td style="padding:6px 9px;font-family:Rajdhani;color:#7a93b0;font-size:.75rem;">'
                f'{r["team_emoji"]} {r["team"]}</td>'
                f'<td style="padding:6px 9px;font-family:Rajdhani;font-weight:700;color:#e2e8f0;">'
                f'{r["port_emoji"]} {r["port"]}</td>'
                f'<td style="padding:6px 9px;font-family:Share Tech Mono;font-size:.68rem;color:#7a93b0;">'
                f'{r["strategy"]}</td>'
                f'<td style="padding:6px 9px;font-family:Share Tech Mono;">${r["total"]:,.0f}</td>'
                f'<td style="padding:6px 9px;color:{pnl_col};font-family:Share Tech Mono;">'
                f'{sign}${abs(r["pnl"]):,.0f}</td>'
                f'<td style="padding:6px 9px;color:{pnl_col};font-family:Share Tech Mono;font-weight:bold;">'
                f'{arr} {abs(r["pct"]):.2f}%</td>'
                f'<td style="padding:6px 9px;font-family:Share Tech Mono;color:#7a93b0;">'
                f'${r["cash"]:,.0f}</td>'
                f'<td style="padding:6px 9px;color:#7a93b0;text-align:center;">{r["n_positions"]}</td>'
                f'<td style="padding:6px 9px;color:#7a93b0;text-align:center;">{r["n_trades"]}</td>'
                f'</tr>'
            )

        st.markdown(
            f'<div class="mam-table-wrap"><table class="mam-table">'
            f'<thead><tr>{th}</tr></thead><tbody>{tbody}</tbody></table></div>',
            unsafe_allow_html=True)

    # ── FIX 3b : Comparaison par équipe ET par typologie de portefeuille ──────
    st.markdown("<br>", unsafe_allow_html=True)
    if all_rows:
        _comparison_by_strategy(all_rows)

    # ── Holdings allocation donut (aggregated) ─────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    section_title("RÉPARTITION GLOBALE PAR ACTIF", "🥧")

    holdings_by_ticker: dict[str, float] = {}
    for team in teams.values():
        for port in team["portfolios"].values():
            if not port.get("name", "").strip():
                continue
            val = value_portfolio(port, prices_dict)
            for pos in val["positions"]:
                t_ = pos["ticker"]
                holdings_by_ticker[t_] = (
                    holdings_by_ticker.get(t_, 0) + pos["market_value"])

    if holdings_by_ticker:
        sorted_h = sorted(holdings_by_ticker.items(), key=lambda x: x[1], reverse=True)
        labels_h = [h[0] for h in sorted_h[:15]]
        values_h = [h[1] for h in sorted_h[:15]]
        if len(sorted_h) > 15:
            labels_h.append("Autres")
            values_h.append(sum(v for _, v in sorted_h[15:]))

        fig_pie = go.Figure(go.Pie(
            labels=labels_h, values=values_h, hole=0.55,
            textfont=dict(family="Share Tech Mono", size=10),
            marker=dict(colors=px.colors.qualitative.Dark24),
            hovertemplate="<b>%{label}</b><br>$%{value:,.0f} (%{percent})<extra></extra>"))
        fig_pie.update_layout(
            **_P, height=320, showlegend=True,
            title=dict(text="Exposition par ticker (toutes équipes)",
                       font=dict(color="#00d4ff", size=12), x=0.01),
            legend=dict(font=dict(size=9, family="Share Tech Mono"),
                        bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Aucune position détenue pour le moment.")


# ── FIX 3b : Comparaison par équipe et par stratégie ─────────────────────────
def _comparison_by_strategy(all_rows: list):
    """Tableau croisé équipe × stratégie + Sharpe approximatif."""
    section_title("COMPARAISON PAR ÉQUIPE & TYPOLOGIE", "⚖️")

    # Construire un DataFrame pivot
    df = pd.DataFrame(all_rows)

    # ── Tableau croisé P&L% : équipe (ligne) × stratégie (colonne) ───────────
    pivot = df.pivot_table(
        index="team", columns="strategy",
        values="pct", aggfunc="mean"
    ).round(2)

    # Affichage HTML stylé
    strategies = list(pivot.columns)
    teams_list = list(pivot.index)

    col_heads = "".join(
        f'<th style="font-family:Rajdhani;font-size:.60rem;color:#00d4ff;'
        f'letter-spacing:.07em;text-transform:uppercase;padding:7px 9px;'
        f'background:rgba(0,212,255,.06);border-bottom:1px solid rgba(0,212,255,.18);">'
        f'{s}</th>' for s in strategies)

    th = (
        f'<th style="font-family:Rajdhani;font-size:.60rem;color:#00d4ff;'
        f'letter-spacing:.07em;text-transform:uppercase;padding:7px 9px;'
        f'background:rgba(0,212,255,.06);border-bottom:1px solid rgba(0,212,255,.18);">'
        f'ÉQUIPE</th>' + col_heads)

    tbody = ""
    for team_name in teams_list:
        row_html = (
            f'<td style="padding:6px 9px;font-family:Rajdhani;font-weight:700;'
            f'color:#e2e8f0;font-size:.78rem;">'
            # find emoji from all_rows
            + next((r["team_emoji"] for r in all_rows if r["team"] == team_name), "")
            + f" {team_name}</td>"
        )
        for strat in strategies:
            val = pivot.loc[team_name, strat] if strat in pivot.columns else float("nan")
            if pd.isna(val):
                row_html += '<td style="padding:6px 9px;color:#475569;text-align:center;">—</td>'
            else:
                col = "#00ff88" if val >= 0 else "#ff3b6b"
                sign = "+" if val >= 0 else ""
                row_html += (
                    f'<td style="padding:6px 9px;font-family:Share Tech Mono;'
                    f'font-weight:bold;color:{col};text-align:center;">'
                    f'{sign}{val:.2f}%</td>')
        tbody += f'<tr style="border-bottom:1px solid rgba(255,255,255,.04);">{row_html}</tr>'

    st.markdown(
        f'<div class="mam-table-wrap"><table class="mam-table">'
        f'<thead><tr>{th}</tr></thead><tbody>{tbody}</tbody></table></div>',
        unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Sharpe approximatif par stratégie (barre) ─────────────────────────────
    section_title("PERFORMANCE PAR STRATÉGIE — P&L MOYEN & SHARPE APPROX.", "📐")

    strat_stats = []
    for strat, grp in df.groupby("strategy"):
        pcts    = grp["pct"].values
        mean_r  = float(np.mean(pcts))
        std_r   = float(np.std(pcts)) if len(pcts) > 1 else 0.0
        sharpe  = mean_r / std_r if std_r > 0 else 0.0
        best    = grp.loc[grp["pct"].idxmax(), "team"] if len(grp) > 0 else "—"
        strat_stats.append({
            "strategy": strat,
            "mean_pct": mean_r,
            "sharpe": sharpe,
            "best_team": best,
            "count": len(grp),
        })

    strat_stats_sorted = sorted(strat_stats, key=lambda x: x["sharpe"], reverse=True)

    col_bar, col_sharpe = st.columns(2)

    with col_bar:
        section_title("P&L MOYEN PAR STRATÉGIE", "📊")
        fig_s = go.Figure(go.Bar(
            x=[s["strategy"] for s in strat_stats_sorted],
            y=[s["mean_pct"] for s in strat_stats_sorted],
            marker_color=["rgba(0,255,136,.7)" if s["mean_pct"] >= 0
                          else "rgba(255,59,107,.7)" for s in strat_stats_sorted],
            text=[f'{s["mean_pct"]:+.2f}%' for s in strat_stats_sorted],
            textposition="outside",
            hovertemplate="%{x}<br>P&L moy: %{y:+.2f}%<extra></extra>"))
        fig_s.add_hline(y=0, line_color="rgba(255,255,255,.2)")
        fig_s.update_layout(**_P, height=260,
            xaxis=dict(showgrid=False, tickangle=-25),
            yaxis=dict(title="P&L moy (%)", gridcolor="rgba(255,255,255,.04)"))
        st.plotly_chart(fig_s, use_container_width=True)

    with col_sharpe:
        section_title("SHARPE APPROX. PAR STRATÉGIE", "⭐")
        fig_sh = go.Figure(go.Bar(
            x=[s["strategy"] for s in strat_stats_sorted],
            y=[s["sharpe"] for s in strat_stats_sorted],
            marker_color=["rgba(0,212,255,.7)" if s["sharpe"] >= 1
                          else "rgba(124,58,237,.7)" if s["sharpe"] >= 0
                          else "rgba(255,59,107,.7)" for s in strat_stats_sorted],
            text=[f'{s["sharpe"]:.2f}' for s in strat_stats_sorted],
            textposition="outside",
            hovertemplate="%{x}<br>Sharpe: %{y:.2f}<extra></extra>"))
        fig_sh.add_hline(y=1, line_color="rgba(255,215,0,.4)", line_dash="dot",
                         annotation_text="Sharpe=1 (cible)",
                         annotation_font_color="#ffd700")
        fig_sh.add_hline(y=0, line_color="rgba(255,255,255,.15)")
        fig_sh.update_layout(**_P, height=260,
            xaxis=dict(showgrid=False, tickangle=-25),
            yaxis=dict(title="Sharpe Ratio approx.", gridcolor="rgba(255,255,255,.04)"))
        st.plotly_chart(fig_sh, use_container_width=True)

    # ── Tableau récap par stratégie ───────────────────────────────────────────
    hdr2 = ["Stratégie", "Nb Ports", "P&L Moy (%)", "Sharpe Approx.", "Meilleure équipe"]
    th2  = "".join(
        f'<th style="font-family:Rajdhani;font-size:.60rem;color:#00d4ff;'
        f'letter-spacing:.07em;text-transform:uppercase;padding:7px 9px;'
        f'background:rgba(0,212,255,.06);border-bottom:1px solid rgba(0,212,255,.18);">'
        f'{c}</th>' for c in hdr2)

    tbody2 = ""
    for s in strat_stats_sorted:
        pnl_col  = "#00ff88" if s["mean_pct"] >= 0 else "#ff3b6b"
        sh_col   = "#00d4ff" if s["sharpe"] >= 1 else "#ffd700" if s["sharpe"] >= 0 else "#ff3b6b"
        sign     = "+" if s["mean_pct"] >= 0 else ""
        tbody2  += (
            f'<tr style="border-bottom:1px solid rgba(255,255,255,.04);">'
            f'<td style="padding:6px 9px;font-family:Rajdhani;font-weight:700;'
            f'color:#e2e8f0;">{s["strategy"]}</td>'
            f'<td style="padding:6px 9px;font-family:Share Tech Mono;'
            f'color:#7a93b0;text-align:center;">{s["count"]}</td>'
            f'<td style="padding:6px 9px;font-family:Share Tech Mono;'
            f'font-weight:bold;color:{pnl_col};text-align:center;">'
            f'{sign}{s["mean_pct"]:.2f}%</td>'
            f'<td style="padding:6px 9px;font-family:Share Tech Mono;'
            f'font-weight:bold;color:{sh_col};text-align:center;">'
            f'{s["sharpe"]:.2f}</td>'
            f'<td style="padding:6px 9px;font-family:Rajdhani;'
            f'color:#94a3b8;">{s["best_team"]}</td>'
            f'</tr>'
        )

    st.markdown(
        f'<div class="mam-table-wrap"><table class="mam-table">'
        f'<thead><tr>{th2}</tr></thead><tbody>{tbody2}</tbody></table></div>',
        unsafe_allow_html=True)


# ── Single portfolio view ─────────────────────────────────────────────────────
def _portfolio_view(team: dict, team_id: str, port: dict, port_id: str,
                    prices_dict: dict, state: dict):

    section_title(f'{port["emoji"]} {port["name"]} — {team["emoji"]} {team["name"]}', "📊")

    val   = value_portfolio(port, prices_dict)
    total = val["total"]
    cash  = val["cash"]
    init  = float(port.get("initial_cash", 1_000_000))
    pnl   = total - init
    pct   = pnl / init * 100 if init else 0
    n_pos = len(val["positions"])

    # Record NAV history
    history = port.get("history", [])
    now_str = datetime.now().isoformat()
    if not history or history[-1].get("date", "")[:10] != now_str[:10]:
        history.append({"date": now_str, "value": total})
        state["teams"][team_id]["portfolios"][port_id]["history"] = history[-365:]
        persist()

    # ── KPI strip ──────────────────────────────────────────────────────────────
    metric_row([
        {"label": "Valeur totale",      "value": f"${total:,.2f}",  "color": ""},
        {"label": "Cash disponible",    "value": f"${cash:,.2f}",   "color": ""},
        {"label": "P&L Total",          "value": f"${pnl:+,.2f}",
         "color": "positive" if pnl >= 0 else "negative"},
        {"label": "Rendement",          "value": f"{pct:+.2f}%",
         "color": "positive" if pct >= 0 else "negative"},
        {"label": "Positions ouvertes", "value": str(n_pos),        "color": ""},
        {"label": "Stratégie",          "value": port.get("strategy", "—"), "color": ""},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    tab_holdings, tab_nav, tab_risk, tab_mwr = st.tabs([
        "💼 POSITIONS",
        "📈 NAV & PERFORMANCE",
        "⚠️ RISQUE",
        "📐 MWR / TWR",
    ])

    with tab_holdings:
        _holdings_tab(val, prices_dict)

    with tab_nav:
        _nav_tab(history, total, init)

    with tab_risk:
        _risk_tab(history, port)

    with tab_mwr:
        _performance_tab(port, history, init, total)


# ── Holdings tab ──────────────────────────────────────────────────────────────
def _holdings_tab(val: dict, prices_dict: dict):
    positions = val["positions"]
    cash      = val["cash"]

    if not positions:
        st.info("📭 Aucune position ouverte. Tradez depuis le Trading Desk !")
        st.markdown(
            f'<div style="font-family:Share Tech Mono;font-size:.8rem;color:#7a93b0;'
            f'text-align:center;margin-top:16px;">Cash disponible : '
            f'<b style="color:#00d4ff;">${cash:,.2f}</b></div>',
            unsafe_allow_html=True)
        return

    # ── FIX 1 : utiliser .get() pour éviter KeyError "unrealized_pnl" ─────────
    total_mkt = sum(p.get("market_value", 0.0) for p in positions)
    total_pnl = sum(p.get("unrealized_pnl", 0.0) for p in positions)

    metric_row([
        {"label": "Positions",        "value": str(len(positions)), "color": ""},
        {"label": "Valeur de marché", "value": f"${total_mkt:,.2f}", "color": ""},
        {"label": "P&L non réalisé",  "value": f"${total_pnl:+,.2f}",
         "color": "positive" if total_pnl >= 0 else "negative"},
        {"label": "Cash",             "value": f"${cash:,.2f}", "color": ""},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    # Holdings table
    hdr = ["Ticker", "Quantité", "Prix moyen", "Prix marché",
           "Valeur marché", "P&L ($)", "P&L (%)", "Poids"]
    th  = "".join(
        f'<th style="font-family:Rajdhani;font-size:.62rem;color:#00d4ff;'
        f'letter-spacing:.08em;text-transform:uppercase;padding:7px 9px;'
        f'background:rgba(0,212,255,.06);border-bottom:1px solid rgba(0,212,255,.18);">'
        f'{c}</th>' for c in hdr)

    total_val = total_mkt + cash
    tbody = ""
    for pos in sorted(positions, key=lambda x: x.get("market_value", 0), reverse=True):
        # FIX 1 : .get() sur chaque clé potentiellement absente
        unrealized = pos.get("unrealized_pnl", 0.0)
        mkt_val    = pos.get("market_value",   0.0)
        avg_price  = pos.get("avg_price",      0.0)
        cur_price  = pos.get("price",          0.0)
        qty        = pos.get("qty",            0.0)
        ticker     = pos.get("ticker",         "?")

        pnl_col = "#00ff88" if unrealized >= 0 else "#ff3b6b"
        sign    = "+" if unrealized >= 0 else ""
        arr     = "▲" if unrealized > 0 else "▼"
        weight  = mkt_val / total_val * 100 if total_val else 0
        pnl_pct = (cur_price - avg_price) / avg_price * 100 if avg_price else 0

        tbody += (
            f'<tr style="border-bottom:1px solid rgba(255,255,255,.04);">'
            f'<td style="padding:7px 9px;font-family:Rajdhani;font-size:.95rem;'
            f'font-weight:700;color:#00d4ff;">{ticker}</td>'
            f'<td style="padding:7px 9px;font-family:Share Tech Mono;">{qty:,.4f}</td>'
            f'<td style="padding:7px 9px;font-family:Share Tech Mono;">${avg_price:,.4f}</td>'
            f'<td style="padding:7px 9px;font-family:Share Tech Mono;">${cur_price:,.4f}</td>'
            f'<td style="padding:7px 9px;font-family:Share Tech Mono;color:#e2e8f0;">'
            f'${mkt_val:,.2f}</td>'
            f'<td style="padding:7px 9px;color:{pnl_col};font-family:Share Tech Mono;">'
            f'{sign}${abs(unrealized):,.2f}</td>'
            f'<td style="padding:7px 9px;color:{pnl_col};font-weight:bold;">'
            f'{arr} {abs(pnl_pct):.2f}%</td>'
            f'<td style="padding:7px 9px;">'
            f'<div style="background:rgba(0,212,255,.15);border-radius:3px;height:6px;'
            f'overflow:hidden;"><div style="width:{min(weight,100):.0f}%;height:100%;'
            f'background:rgba(0,212,255,.7);"></div></div>'
            f'<span style="font-family:Share Tech Mono;font-size:.65rem;color:#7a93b0;">'
            f'{weight:.1f}%</span></td>'
            f'</tr>'
        )

    st.markdown(
        f'<div class="mam-table-wrap"><table class="mam-table">'
        f'<thead><tr>{th}</tr></thead><tbody>{tbody}</tbody></table></div>',
        unsafe_allow_html=True)

    # Allocation donut
    st.markdown("<br>", unsafe_allow_html=True)
    section_title("RÉPARTITION DU PORTEFEUILLE", "🥧")

    labels = [p.get("ticker", "?") for p in positions] + ["Cash"]
    values = [p.get("market_value", 0.0) for p in positions] + [cash]

    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        textfont=dict(family="Share Tech Mono", size=10),
        marker=dict(colors=px.colors.qualitative.Dark24),
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f} (%{percent})<extra></extra>"))
    fig.update_layout(**_P, height=300, showlegend=True,
        legend=dict(font=dict(size=9, family="Share Tech Mono"), bgcolor="rgba(0,0,0,0)"))
    st.plotly_chart(fig, use_container_width=True)


# ── NAV tab ───────────────────────────────────────────────────────────────────
def _nav_tab(history: list, current_total: float, init: float):
    section_title("VALEUR NETTE D'ACTIF (NAV)", "📈")

    if len(history) < 2:
        st.info("L'historique de NAV s'enrichit à chaque visite du Dashboard.")
        _nav_placeholder(current_total, init)
        return

    df = pd.DataFrame(history)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates("date")
    df["pct"] = (df["value"] / init - 1) * 100

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.7, 0.3], vertical_spacing=0.04)

    fig.add_trace(go.Scatter(
        x=df["date"], y=df["value"],
        mode="lines+markers", marker=dict(size=4),
        line=dict(color="#00d4ff", width=2.5),
        fill="tozeroy", fillcolor="rgba(0,212,255,.06)",
        name="NAV", hovertemplate="%{x|%d %b %Y}<br>$%{y:,.2f}<extra></extra>"),
        row=1, col=1)
    fig.add_hline(y=init, line_color="rgba(255,215,0,.4)", line_dash="dot",
                  annotation_text=f"Capital initial ${init:,.0f}",
                  annotation_font_color="#ffd700", row=1, col=1)

    pnl_colors = ["rgba(0,255,136,.6)" if v >= 0 else "rgba(255,59,107,.6)"
                  for v in df["pct"]]
    fig.add_trace(go.Bar(
        x=df["date"], y=df["pct"],
        name="Rendement (%)", marker_color=pnl_colors,
        hovertemplate="%{x|%d %b}<br>%{y:+.2f}%<extra></extra>"),
        row=2, col=1)
    fig.add_hline(y=0, line_color="rgba(255,255,255,.2)", row=2, col=1)

    fig.update_layout(**_P, height=400,
        legend=dict(orientation="h", y=1.02, font=dict(size=10)),
        yaxis=dict(title="Valeur ($)",     gridcolor="rgba(255,255,255,.04)"),
        yaxis2=dict(title="Rendement (%)", gridcolor="rgba(255,255,255,.04)"))
    st.plotly_chart(fig, use_container_width=True)

    max_nav  = float(df["value"].max())
    min_nav  = float(df["value"].min())
    last_ret = float(df["pct"].iloc[-1])

    metric_row([
        {"label": "NAV actuelle",    "value": f"${current_total:,.2f}", "color": ""},
        {"label": "NAV max",         "value": f"${max_nav:,.2f}",       "color": "positive"},
        {"label": "NAV min",         "value": f"${min_nav:,.2f}",       "color": "negative"},
        {"label": "Rendement total", "value": f"{last_ret:+.2f}%",
         "color": "positive" if last_ret >= 0 else "negative"},
    ])


def _nav_placeholder(total: float, init: float):
    pnl  = total - init
    pct  = pnl / init * 100 if init else 0
    col  = "#00ff88" if pnl >= 0 else "#ff3b6b"
    sign = "+" if pnl >= 0 else ""
    st.markdown(
        f'<div style="background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.2);'
        f'border-radius:10px;padding:24px;text-align:center;">'
        f'<div style="font-family:Rajdhani;font-size:.72rem;color:#7a93b0;letter-spacing:.1em;">'
        f'VALEUR ACTUELLE</div>'
        f'<div style="font-family:Share Tech Mono;font-size:2.2rem;color:#e2e8f0;'
        f'font-weight:bold;margin:8px 0;">${total:,.2f}</div>'
        f'<div style="font-family:Share Tech Mono;font-size:1rem;color:{col};">'
        f'{sign}${abs(pnl):,.2f} ({sign}{abs(pct):.2f}%)</div>'
        f'</div>',
        unsafe_allow_html=True)


# ── Risk tab ──────────────────────────────────────────────────────────────────
def _risk_tab(history: list, port: dict):
    section_title("MÉTRIQUES DE RISQUE", "⚠️")

    if len(history) < 5:
        st.info("Données insuffisantes pour le calcul des métriques (min. 5 observations).")
        return

    df      = pd.DataFrame(history).sort_values("date")
    returns = df["value"].pct_change().dropna()
    metrics = compute_risk_metrics(returns)

    if not metrics:
        st.warning("Impossible de calculer les métriques de risque.")
        return

    metric_row([
        {"label": "Sharpe Ratio",    "value": f'{metrics["sharpe"]:.3f}',
         "color": "positive" if metrics["sharpe"] >= 1 else "neutral" if metrics["sharpe"] >= 0 else "negative"},
        {"label": "Sortino Ratio",   "value": f'{metrics["sortino"]:.3f}',
         "color": "positive" if metrics["sortino"] >= 1 else "neutral"},
        {"label": "Max Drawdown",    "value": f'{metrics["max_drawdown"]*100:.2f}%',
         "color": "negative"},
        {"label": "Vol. annualisée", "value": f'{metrics["ann_vol"]*100:.2f}%', "color": ""},
        {"label": "VaR 95% (1j)",    "value": f'{metrics["var_95"]*100:.2f}%',  "color": "negative"},
        {"label": "CVaR 95%",        "value": f'{metrics["cvar_95"]*100:.2f}%', "color": "negative"},
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    section_title("DRAWDOWN HISTORIQUE", "📉")
    cumul    = (1 + returns).cumprod()
    roll_max = cumul.cummax()
    drawdown = (cumul - roll_max) / roll_max * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"].iloc[1:], y=drawdown,
        mode="lines", line=dict(color="#ff3b6b", width=1.5),
        fill="tozeroy", fillcolor="rgba(255,59,107,.08)",
        hovertemplate="%{x|%d %b}<br>DD: %{y:.2f}%<extra></extra>", name="Drawdown"))
    fig.add_hline(y=0, line_color="rgba(255,255,255,.2)")
    fig.update_layout(**_P, height=200,
        xaxis=dict(showgrid=False),
        yaxis=dict(title="Drawdown (%)", gridcolor="rgba(255,255,255,.04)"))
    st.plotly_chart(fig, use_container_width=True)

    section_title("DISTRIBUTION DES RENDEMENTS", "📊")
    fig2 = go.Figure()
    fig2.add_trace(go.Histogram(
        x=returns * 100, nbinsx=30,
        marker_color="rgba(0,212,255,.5)",
        hovertemplate="Rendement: %{x:.2f}%<br>Fréq: %{y}<extra></extra>",
        name="Rendements"))
    if "var_95" in metrics:
        fig2.add_vline(x=metrics["var_95"] * 100, line_color="#ff3b6b", line_dash="dot",
                       annotation_text=f'VaR 95%: {metrics["var_95"]*100:.2f}%',
                       annotation_font_color="#ff3b6b")
    fig2.add_vline(x=0, line_color="rgba(255,255,255,.2)")
    fig2.update_layout(**_P, height=200,
        xaxis=dict(title="Rendement (%)", gridcolor="rgba(255,255,255,.04)"),
        yaxis=dict(title="Fréquence",     gridcolor="rgba(255,255,255,.04)"))
    st.plotly_chart(fig2, use_container_width=True)


# ── MWR / TWR tab ─────────────────────────────────────────────────────────────
def _performance_tab(port: dict, history: list, init: float, current: float):
    section_title("MWR (Money-Weighted Return) & TWR (Time-Weighted Return)", "📐")

    st.markdown("""
    <div style="background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.2);
    border-radius:8px;padding:12px 16px;margin-bottom:16px;font-family:Share Tech Mono;
    font-size:.73rem;color:#94a3b8;line-height:1.8;">
    📐 <b style="color:#00d4ff;">MWR</b> — Taux de rendement pondéré par les flux (IRR interne).<br>
    📐 <b style="color:#00d4ff;">TWR</b> — Taux de rendement pondéré par le temps (indépendant des flux).<br>
    Le TWR élimine l'effet de la taille et du timing des apports/retraits.
    </div>""", unsafe_allow_html=True)

    trades = port.get("trades", [])
    twr    = _compute_twr(history)
    mwr    = _compute_mwr(init, current, trades)

    col1, col2 = st.columns(2)
    twr_col = "#00ff88" if twr >= 0 else "#ff3b6b"
    mwr_col = "#00ff88" if mwr >= 0 else "#ff3b6b"

    with col1:
        st.markdown(
            f'<div style="background:rgba(0,212,255,.06);border:1px solid rgba(0,212,255,.2);'
            f'border-radius:10px;padding:20px;text-align:center;">'
            f'<div style="font-family:Rajdhani;font-size:.72rem;color:#7a93b0;'
            f'letter-spacing:.1em;margin-bottom:8px;">MWR (IRR approximé)</div>'
            f'<div style="font-family:Share Tech Mono;font-size:2.5rem;color:{mwr_col};'
            f'font-weight:bold;">{mwr:+.2f}%</div>'
            f'<div style="font-family:Share Tech Mono;font-size:.68rem;color:#475569;margin-top:6px;">'
            f'Pondéré par les flux de trésorerie</div>'
            f'</div>', unsafe_allow_html=True)

    with col2:
        st.markdown(
            f'<div style="background:rgba(124,58,237,.06);border:1px solid rgba(124,58,237,.2);'
            f'border-radius:10px;padding:20px;text-align:center;">'
            f'<div style="font-family:Rajdhani;font-size:.72rem;color:#7a93b0;'
            f'letter-spacing:.1em;margin-bottom:8px;">TWR (Time-Weighted)</div>'
            f'<div style="font-family:Share Tech Mono;font-size:2.5rem;color:{twr_col};'
            f'font-weight:bold;">{twr:+.2f}%</div>'
            f'<div style="font-family:Share Tech Mono;font-size:.68rem;color:#475569;margin-top:6px;">'
            f'Indépendant du timing des flux</div>'
            f'</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if len(history) >= 2:
        section_title("RENDEMENTS PAR SOUS-PÉRIODE", "📅")
        df  = pd.DataFrame(history).sort_values("date")
        df["ret"]  = df["value"].pct_change() * 100
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%d/%m")

        fig = go.Figure(go.Bar(
            x=df["date"].iloc[1:], y=df["ret"].iloc[1:],
            marker_color=["rgba(0,255,136,.7)" if v >= 0 else "rgba(255,59,107,.7)"
                          for v in df["ret"].iloc[1:]],
            hovertemplate="%{x}<br>%{y:+.2f}%<extra></extra>"))
        fig.add_hline(y=0, line_color="rgba(255,255,255,.2)")
        fig.update_layout(**_P, height=220,
            xaxis=dict(title="Date", showgrid=False, tickangle=-30),
            yaxis=dict(title="Rendement (%)", gridcolor="rgba(255,255,255,.04)"))
        st.plotly_chart(fig, use_container_width=True)

    section_title("SYNTHÈSE DES TRANSACTIONS", "📋")
    if trades:
        buys  = [t for t in trades if t.get("action") == "BUY"]
        sells = [t for t in trades if t.get("action") == "SELL"]
        vol   = sum(t.get("total", 0) for t in trades)
        metric_row([
            {"label": "Total trades", "value": str(len(trades)), "color": ""},
            {"label": "BUY",          "value": str(len(buys)),   "color": "positive"},
            {"label": "SELL",         "value": str(len(sells)),  "color": "negative"},
            {"label": "Volume ($)",   "value": f"${vol:,.0f}",   "color": ""},
        ])
    else:
        st.info("Aucune transaction enregistrée.")


def _compute_twr(history: list) -> float:
    if len(history) < 2:
        return 0.0
    try:
        df   = pd.DataFrame(history).sort_values("date")
        rets = df["value"].pct_change().dropna()
        return float((1 + rets).prod() - 1) * 100
    except Exception:
        return 0.0


def _compute_mwr(init: float, current: float, trades: list) -> float:
    try:
        if init <= 0:
            return 0.0
        return (current - init) / init * 100
    except Exception:
        return 0.0
