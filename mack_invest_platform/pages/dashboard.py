# pages/dashboard.py  —  MAM v5.0
"""
Dashboard : portefeuilles de l'équipe active.
- Ticker tape animé avec badges carrés, 2 derniers items fixes
- P&L live : (prix_actuel - avg_entry) * qty  via fast_info.last_price
- Var. 1J : (last_price - previous_close) / previous_close
- Colonnes : Ticker | Qté | Px Entrée | Px Actuel | Var.1J | Valeur | P&L $ | P&L %
- Vert/Rouge selon signe
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
from datetime import datetime

from components.ui import section_title
from utils.data import get_or_init_state, get_multi_prices, get_price_change

# ── Tickers affichés dans le bandeau du dashboard ──────────────────────────────
_TAPE_SYMBOLS = [
    ("^GSPC",    "S&P500"),  ("^IXIC",   "NASDAQ"), ("^DJI",    "DOW"),
    ("^FCHI",    "CAC40"),   ("^GDAXI",  "DAX"),    ("^FTSE",   "FTSE"),
    ("GC=F",     "GOLD"),    ("CL=F",    "WTI"),    ("BTC-USD", "BTC"),
    ("ETH-USD",  "ETH"),     ("EURUSD=X","EUR/USD"),("^VIX",    "VIX"),
    ("AAPL",     "AAPL"),    ("NVDA",    "NVDA"),   ("MSFT",    "MSFT"),
    ("TSLA",     "TSLA"),    ("AMZN",    "AMZN"),   ("META",    "META"),
]
# Les 2 derniers sont fixes (non animés)
_FIXED_COUNT = 2


def _build_tape(prices: dict) -> str:
    """
    Build ticker tape HTML.
    Animated items : _TAPE_SYMBOLS[:-_FIXED_COUNT]
    Fixed items    : _TAPE_SYMBOLS[-_FIXED_COUNT:]
    Each item has a small square badge with the label.
    """
    def item_html(sym: str, label: str, animated: bool) -> str:
        if sym not in prices:
            return ""
        px, pct = prices[sym]
        arr  = "▲" if pct >= 0 else "▼"
        cls  = "tape-up" if pct >= 0 else "tape-dn"
        sign = "+" if pct >= 0 else ""
        if px >= 1000:
            px_str = f"${px:,.0f}"
        elif px >= 1:
            px_str = f"${px:,.2f}"
        else:
            px_str = f"${px:,.5f}"
        badge_col = "#00d4ff" if animated else "#7c3aed"
        return (
            f'<span class="tape-item">'
            f'<span class="tape-badge" style="border-color:{badge_col};color:{badge_col};">'
            f'{label}</span>'
            f'<span class="tape-px">{px_str}</span>'
            f'<span class="{cls}">{arr}{sign}{abs(pct):.2f}%</span>'
            f'</span>'
        )

    # Animated part (duplicated for seamless loop)
    animated_syms = _TAPE_SYMBOLS[:-_FIXED_COUNT]
    anim_html = "".join(item_html(s, l, True) for s, l in animated_syms)
    anim_block = (
        f'<div class="tape-track">{anim_html}{anim_html}</div>'
    )

    # Fixed part
    fixed_syms = _TAPE_SYMBOLS[-_FIXED_COUNT:]
    fixed_html = "".join(item_html(s, l, False) for s, l in fixed_syms)
    fixed_block = f'<div class="tape-fixed">{fixed_html}</div>'

    return f"""
<style>
.tape-wrap {{
    display: flex;
    align-items: center;
    width: 100%;
    height: 28px;
    background: rgba(0,8,18,0.96);
    border: 1px solid rgba(0,212,255,0.16);
    border-radius: 5px;
    overflow: hidden;
    margin-bottom: 6px;
    position: relative;
}}
.tape-scroll-zone {{
    flex: 1;
    overflow: hidden;
    position: relative;
    height: 100%;
    display: flex;
    align-items: center;
}}
.tape-track {{
    display: flex;
    white-space: nowrap;
    animation: tape-anim 80s linear infinite;
    height: 100%;
    align-items: center;
}}
.tape-track:hover {{ animation-play-state: paused; }}
@keyframes tape-anim {{
    0%   {{ transform: translateX(0); }}
    100% {{ transform: translateX(-50%); }}
}}
.tape-fixed {{
    display: flex;
    align-items: center;
    height: 100%;
    border-left: 1px solid rgba(124,58,237,0.3);
    background: rgba(124,58,237,0.06);
    padding: 0 4px;
    flex-shrink: 0;
}}
.tape-item {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 0 10px;
    border-right: 1px solid rgba(255,255,255,0.05);
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.63rem;
}}
.tape-badge {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 42px;
    height: 16px;
    border: 1px solid;
    border-radius: 2px;
    font-family: 'Rajdhani', sans-serif;
    font-weight: 700;
    font-size: 0.58rem;
    letter-spacing: 0.04em;
    flex-shrink: 0;
}}
.tape-px  {{ color: #e2e8f0; font-size: 0.63rem; }}
.tape-up  {{ color: #00ff88; font-size: 0.60rem; }}
.tape-dn  {{ color: #ff3b6b; font-size: 0.60rem; }}
</style>
<div class="tape-wrap">
  <div class="tape-scroll-zone">{anim_block}</div>
  {fixed_block}
</div>
"""


def render():
    state   = get_or_init_state()
    team_id = st.session_state.get("active_team")
    teams   = state.get("teams", {})

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        '<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;letter-spacing:.12em;'
        'color:#00ff88;margin:0 0 6px;text-shadow:0 0 30px rgba(0,255,136,.4);">'
        '🏠 DASHBOARD — MAM</h1>',
        unsafe_allow_html=True,
    )

    # ── Ticker tape ───────────────────────────────────────────────────────────
    tape_tickers = tuple(s for s, _ in _TAPE_SYMBOLS)
    tape_prices  = get_multi_prices(tape_tickers)
    st.markdown(_build_tape(tape_prices), unsafe_allow_html=True)

    if not team_id or team_id not in teams:
        st.info("👈 Sélectionnez ou créez une équipe dans la barre latérale.")
        _empty_state()
        return

    team  = teams[team_id]
    ports = team.get("portfolios", {})

    # Portefeuilles avec un nom ET des positions
    user_ports = {
        pid: p for pid, p in ports.items()
        if p.get("name") and p.get("holdings")
    }

    if not user_ports:
        st.info("Aucun portefeuille avec des positions. Rendez-vous dans **Trading Desk** pour investir.")
        _empty_state()
        return

    # ── Fetch live prices for all held tickers ────────────────────────────────
    all_tickers: set[str] = set()
    for p in user_ports.values():
        all_tickers.update(p.get("holdings", {}).keys())

    live = get_multi_prices(tuple(all_tickers))
    # live[tk] = (current_price, pct_1d_change)

    # ── Compute KPIs ──────────────────────────────────────────────────────────
    total_cash     = 0.0
    total_mkt      = 0.0
    total_pnl      = 0.0
    total_cost     = 0.0
    ports_with_pos = 0
    port_summaries = []

    for pid, port in user_ports.items():
        holdings = port.get("holdings", {})
        cash     = port.get("cash", 0.0)
        total_cash += cash
        ports_with_pos += 1

        mkt = cost = pnl = 0.0
        positions = []

        for tk, pos in holdings.items():
            qty        = pos.get("qty", 0)
            avg        = pos.get("avg_price", 0.0)
            curr, pct_d = live.get(tk, (avg, 0.0))
            pos_mkt    = qty * curr
            pos_cost   = qty * avg
            pos_pnl    = pos_mkt - pos_cost          # live unrealised P&L
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

    total_aum     = total_cash + total_mkt
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0

    # ── KPI Cards ─────────────────────────────────────────────────────────────
    kpi_style = (
        'background:rgba(0,212,255,.05);border:1px solid rgba(0,212,255,.15);'
        'border-radius:8px;padding:14px 16px;'
    )
    pnl_col = "#00ff88" if total_pnl >= 0 else "#ff3b6b"
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f'<div style="{kpi_style}">'
            f'<div style="font-family:Rajdhani;font-size:.68rem;color:#7a93b0;'
            f'letter-spacing:.12em;text-transform:uppercase;">AUM Total</div>'
            f'<div style="font-family:Share Tech Mono;font-size:1.5rem;color:#e2e8f0;">'
            f'${total_aum:,.0f}</div>'
            f'<div style="font-size:.7rem;color:#475569;">{len(user_ports)} portefeuille(s)</div>'
            f'</div>', unsafe_allow_html=True,
        )
    with c2:
        cash_pct = f"{total_cash/total_aum*100:.1f}% du portf." if total_aum > 0 else "—"
        st.markdown(
            f'<div style="{kpi_style}">'
            f'<div style="font-family:Rajdhani;font-size:.68rem;color:#7a93b0;'
            f'letter-spacing:.12em;text-transform:uppercase;">Cash Total</div>'
            f'<div style="font-family:Share Tech Mono;font-size:1.5rem;color:#00d4ff;">'
            f'${total_cash:,.0f}</div>'
            f'<div style="font-size:.7rem;color:#475569;">{cash_pct}</div>'
            f'</div>', unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div style="{kpi_style}">'
            f'<div style="font-family:Rajdhani;font-size:.68rem;color:#7a93b0;'
            f'letter-spacing:.12em;text-transform:uppercase;">Valeur Marché</div>'
            f'<div style="font-family:Share Tech Mono;font-size:1.5rem;color:#e2e8f0;">'
            f'${total_mkt:,.0f}</div>'
            f'<div style="font-size:.7rem;color:#475569;">{ports_with_pos} portf. en position</div>'
            f'</div>', unsafe_allow_html=True,
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
            f'</div>', unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Portfolio cards ───────────────────────────────────────────────────────
    section_title("MES PORTEFEUILLES", "📁")

    for summary in port_summaries:
        if not summary["positions"]:
            continue

        port      = summary["port"]
        mkt_val   = summary["mkt_value"]
        pnl       = summary["pnl"]
        cost      = summary["cost"]
        positions = summary["positions"]
        cash      = port.get("cash", 0.0)
        ppct      = (pnl / cost * 100) if cost > 0 else 0.0
        p_col     = "#00ff88" if pnl >= 0 else "#ff3b6b"
        sg        = "+" if pnl >= 0 else ""
        emoji     = port.get("emoji", "📁")
        name      = port.get("name", "—")
        strategy  = port.get("strategy", "")

        # Card header
        st.markdown(
            f'<div style="background:rgba(0,10,25,.6);border:1px solid rgba(0,212,255,.18);'
            f'border-radius:10px;padding:16px 20px;margin-bottom:12px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'margin-bottom:12px;">'
            f'<div>'
            f'<span style="font-family:Rajdhani;font-size:1.1rem;font-weight:700;'
            f'color:#e2e8f0;">{emoji} {name}</span>'
            f'<span style="font-family:Rajdhani;font-size:.65rem;color:#475569;'
            f'letter-spacing:.12em;text-transform:uppercase;margin-left:10px;">{strategy}</span>'
            f'</div>'
            f'<div style="text-align:right;">'
            f'<div style="font-family:Share Tech Mono;font-size:.82rem;color:#e2e8f0;">'
            f'AUM <b>${cash + mkt_val:,.0f}</b></div>'
            f'<div style="font-family:Share Tech Mono;font-size:.78rem;color:{p_col};">'
            f'P&L {sg}${abs(pnl):,.2f} ({sg}{abs(ppct):.2f}%)</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # ── Positions table ────────────────────────────────────────────────────
        # Colonnes : Ticker | Qté | Px Entrée | Px Actuel | Var.1J | Valeur | P&L $ | P&L %
        col_hdrs = ["TICKER", "QTÉ", "PX ENTRÉE", "PX ACTUEL", "VAR. 1J", "VALEUR", "P&L $", "P&L %"]
        th = "".join(
            f'<th style="font-family:Rajdhani;font-size:.63rem;color:#00d4ff;'
            f'letter-spacing:.08em;text-transform:uppercase;padding:6px 10px;'
            f'background:rgba(0,212,255,.06);border-bottom:1px solid rgba(0,212,255,.14);">'
            f'{c}</th>' for c in col_hdrs
        )
        tbody = ""
        for pos in positions:
            tk     = pos["ticker"]
            qty    = pos["qty"]
            avg    = pos["avg"]
            curr   = pos["curr"]
            pct_d  = pos["pct_d"]   # variation vs previous close (1D)
            p_v    = pos["mkt"]     # market value
            p_pnl  = pos["pnl"]     # unrealised P&L vs entry price
            p_cost = pos["cost"]
            p_pct  = (p_pnl / p_cost * 100) if p_cost > 0 else 0.0

            # Colours
            pnl_c  = "#00ff88" if p_pnl > 0 else ("#ff3b6b" if p_pnl < 0 else "#94a3b8")
            day_c  = "#00ff88" if pct_d > 0 else ("#ff3b6b" if pct_d < 0 else "#94a3b8")
            sgp    = "+" if p_pnl > 0 else ""
            ar_pnl = "▲" if p_pnl > 0 else ("▼" if p_pnl < 0 else "▬")
            ar_day = "▲" if pct_d > 0 else ("▼" if pct_d < 0 else "▬")
            sgd    = "+" if pct_d > 0 else ""

            # Price formatting
            fmt = lambda v: f"${v:,.0f}" if v >= 1000 else (f"${v:,.2f}" if v >= 1 else f"${v:,.5f}")

            tbody += (
                f'<tr style="border-bottom:1px solid rgba(255,255,255,.03);">'
                f'<td style="padding:6px 10px;color:#00d4ff;font-weight:bold;'
                f'font-family:Rajdhani;font-size:.82rem;letter-spacing:.06em;">{tk}</td>'
                f'<td style="padding:6px 10px;font-family:Share Tech Mono;font-size:.74rem;">'
                f'{qty:,.4f}</td>'
                f'<td style="padding:6px 10px;color:#7a93b0;font-family:Share Tech Mono;'
                f'font-size:.74rem;">{fmt(avg)}</td>'
                f'<td style="padding:6px 10px;font-family:Share Tech Mono;font-size:.74rem;">'
                f'{fmt(curr)}</td>'
                f'<td style="padding:6px 10px;color:{day_c};font-family:Share Tech Mono;'
                f'font-size:.74rem;">{ar_day} {sgd}{abs(pct_d):.2f}%</td>'
                f'<td style="padding:6px 10px;font-family:Share Tech Mono;font-size:.74rem;">'
                f'${p_v:,.2f}</td>'
                f'<td style="padding:6px 10px;color:{pnl_c};font-weight:bold;'
                f'font-family:Share Tech Mono;font-size:.74rem;">'
                f'{sgp}${abs(p_pnl):,.2f}</td>'
                f'<td style="padding:6px 10px;color:{pnl_c};font-family:Share Tech Mono;'
                f'font-size:.74rem;">{ar_pnl} {sgp}{abs(p_pct):.2f}%</td>'
                f'</tr>'
            )

        st.markdown(
            f'<div style="overflow-x:auto;">'
            f'<table style="width:100%;border-collapse:collapse;color:#e2e8f0;">'
            f'<thead><tr>{th}</tr></thead>'
            f'<tbody>{tbody}</tbody>'
            f'</table></div></div>',
            unsafe_allow_html=True,
        )


def _empty_state():
    st.markdown(
        '<div style="text-align:center;padding:60px 0;">'
        '<div style="font-size:3rem;margin-bottom:16px;">📁</div>'
        '<div style="font-family:Rajdhani;font-size:1.1rem;letter-spacing:.12em;'
        'text-transform:uppercase;color:#475569;">Aucun portefeuille avec des positions</div>'
        '<div style="font-family:Share Tech Mono;font-size:.75rem;color:#334155;'
        'margin-top:8px;">Passez un ordre dans Trading Desk pour voir vos positions ici.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
