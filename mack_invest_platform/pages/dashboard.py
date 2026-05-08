"""
Dashboard: team overview, portfolio summary, quick stats, risk metrics.
ESLSCA Stock Market Game — v2.1
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from components.ui import section_title, metric_row
from utils.data import (
    get_or_init_state, load_assets, get_price,
    value_portfolio, compute_portfolio_metrics,
)

# ── Plotly dark layout defaults ───────────────────────────────────────────────
_PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#94a3b8", family="Share Tech Mono"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.04)", zeroline=False),
    yaxis=dict(gridcolor="rgba(255,255,255,0.04)", zeroline=False),
    margin=dict(l=10, r=10, t=10, b=10),
    showlegend=False,
)


def render():
    state = get_or_init_state()
    teams = state.get("teams", {})

    if not teams:
        st.error("No teams found. Please create teams in the Admin Panel.")
        return

    # Safely resolve active team
    active_team_id = st.session_state.get("active_team")
    if not active_team_id or active_team_id not in teams:
        active_team_id = list(teams.keys())[0]
        st.session_state["active_team"] = active_team_id

    team = teams[active_team_id]

    # ── Page header ──
    st.markdown(
        f'<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;'
        f'letter-spacing:0.12em;color:#00d4ff;margin:0 0 2px;'
        f'text-shadow:0 0 30px rgba(0,212,255,0.5);">'
        f'{team.get("emoji","📊")} {team.get("name","TEAM").upper()} — PORTFOLIO DASHBOARD'
        f'</h1>',
        unsafe_allow_html=True,
    )

    # ── Fetch prices for all holdings ──
    holdings = team.get("holdings", {})
    prices = {}
    for ticker in holdings:
        prices[ticker] = get_price(ticker)

    val     = value_portfolio(team, prices)
    total   = val.get("total", 0.0)
    cash    = val.get("cash", 0.0)
    spot    = val.get("spot_value", 0.0)
    initial = 10_000_000.0

    pnl     = total - initial
    pnl_pct = (pnl / initial * 100) if initial else 0.0

    # ── Top metrics ──
    section_title("PORTFOLIO OVERVIEW", "📡")
    metric_row([
        {"label": "Total Value",    "value": f"${total:,.0f}",  "color": ""},
        {"label": "Cash",           "value": f"${cash:,.0f}",   "color": ""},
        {"label": "Invested",       "value": f"${spot:,.0f}",   "color": ""},
        {
            "label": "Unrealised P&L",
            "value": f"${pnl:+,.0f} ({pnl_pct:+.2f}%)",
            "color": "positive" if pnl >= 0 else "negative",
        },
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])

    # ── Portfolio history chart ──
    with col1:
        section_title("PORTFOLIO VALUE HISTORY", "📈")
        history = team.get("portfolio_history", [])
        if history:
            hist_df = pd.DataFrame(history)
            # Ensure required columns exist
            if "date" in hist_df.columns and "value" in hist_df.columns:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=hist_df["date"],
                    y=hist_df["value"],
                    mode="lines",
                    name="Portfolio",
                    line=dict(color="#00d4ff", width=2.5),
                    fill="tozeroy",
                    fillcolor="rgba(0,212,255,0.06)",
                    hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>",
                ))
                fig.add_hline(
                    y=initial,
                    line_dash="dot",
                    line_color="#ff3b6b",
                    opacity=0.6,
                    annotation_text="Start",
                    annotation_font_color="#ff3b6b",
                )
                fig.update_layout(**_PLOT_LAYOUT, height=260)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Portfolio history has unexpected format.")
        else:
            st.info("No portfolio history yet. Start trading to track value over time.")

    # ── Allocation pie ──
    with col2:
        section_title("ALLOCATION", "🥧")
        positions = val.get("positions", [])
        if positions:
            pie_labels = [p["ticker"] for p in positions] + ["Cash"]
            pie_values = [p["market_value"] for p in positions] + [cash]
            fig2 = go.Figure(go.Pie(
                labels=pie_labels,
                values=pie_values,
                hole=0.55,
                marker=dict(colors=px.colors.qualitative.Dark24),
                textfont=dict(family="Share Tech Mono", size=10),
                hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>",
            ))
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                margin=dict(l=0, r=0, t=0, b=0),
                height=260,
                showlegend=True,
                legend=dict(
                    font=dict(size=10, family="Share Tech Mono"),
                    bgcolor="rgba(0,0,0,0)",
                ),
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No positions yet.")

    # ── Open positions table ──
    section_title("OPEN POSITIONS", "📋")
    positions = val.get("positions", [])
    if positions:
        pos_df = pd.DataFrame(positions)

        # Rename known columns safely
        col_rename = {
            "ticker":         "Ticker",
            "qty":            "Qty",
            "avg_price":      "Avg Price",
            "current_price":  "Last Price",
            "market_value":   "Mkt Value",
            "unreal_pnl":     "Unreal. P&L",
            "pnl_pct":        "P&L %",
        }
        pos_df = pos_df.rename(columns={k: v for k, v in col_rename.items() if k in pos_df.columns})

        # Format numeric columns where they exist
        for c in ["Avg Price", "Last Price", "Mkt Value"]:
            if c in pos_df.columns:
                pos_df[c] = pos_df[c].apply(
                    lambda x: f"{float(x):,.4f}" if _is_numeric(x) else x
                )
        if "Unreal. P&L" in pos_df.columns:
            pos_df["Unreal. P&L"] = pos_df["Unreal. P&L"].apply(
                lambda x: (f"+{float(x):,.0f}" if float(x) >= 0 else f"{float(x):,.0f}")
                if _is_numeric(x) else x
            )
        if "P&L %" in pos_df.columns:
            pos_df["P&L %"] = pos_df["P&L %"].apply(
                lambda x: f"{float(x):+.2f}%" if _is_numeric(x) else x
            )

        st.dataframe(pos_df, use_container_width=True, hide_index=True)
    else:
        st.info("No open positions. Use the Trading Desk to build your portfolio.")

    # ── Risk metrics ──
    section_title("RISK METRICS (LIVE)", "⚠️")
    history = team.get("portfolio_history", [])
    if len(history) >= 5:
        hist_df = pd.DataFrame(history)
        if "value" in hist_df.columns:
            rets = hist_df["value"].pct_change().dropna()
            m = compute_portfolio_metrics(rets)
            if m:
                metric_row([
                    {"label": "Ann. Vol",      "value": f"{m['ann_vol']*100:.2f}%",      "color": ""},
                    {
                        "label": "Sharpe Ratio",
                        "value": f"{m['sharpe']:.2f}",
                        "color": "positive" if m["sharpe"] >= 2 else
                                 ("neutral" if m["sharpe"] >= 1 else "negative"),
                    },
                    {
                        "label": "Max Drawdown",
                        "value": f"{m['max_drawdown']*100:.2f}%",
                        "color": "negative" if m["max_drawdown"] < -0.05 else "positive",
                    },
                    {"label": "VaR 99% 10d",  "value": f"{m['var_99_10d']*100:.2f}%",   "color": ""},
                    {"label": "CVaR 99% 10d", "value": f"{m['cvar_99_10d']*100:.2f}%",  "color": ""},
                ])
            else:
                st.info("Insufficient data to compute risk metrics.")
        else:
            st.info("Portfolio history is missing value data.")
    else:
        st.info("Risk metrics available after 5+ trading days of portfolio history.")

    # ── Recent trades ──
    section_title("RECENT TRADES", "🔄")
    trades = team.get("trades", [])
    if trades:
        # Show last 20 trades, most recent first
        recent = trades[-20:][::-1]
        t_df = pd.DataFrame(recent)
        st.dataframe(t_df, use_container_width=True, hide_index=True)
    else:
        st.info("No trades yet.")


# ── Helper ────────────────────────────────────────────────────────────────────

def _is_numeric(v) -> bool:
    """Return True if v can be safely cast to float."""
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False
