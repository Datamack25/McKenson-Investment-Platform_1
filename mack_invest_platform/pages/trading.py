"""
Trading Desk: Spot trades + European options (Black-Scholes).
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta
from components.ui import section_title, metric_row
from utils.data import (get_or_init_state, persist_state, load_assets,
                        get_price, value_portfolio)
from utils.options import price_option_ticket, bs_price, _time_to_expiry


def _get_contract_mult(ticker: str, assets_df: pd.DataFrame) -> int:
    row = assets_df[assets_df["ticker"] == ticker]
    if not row.empty:
        return int(row["contract_mult"].iloc[0])
    return 1 if "USD" in ticker else 100


def render():
    state = get_or_init_state()
    team_id = st.session_state.get("active_team", list(state["teams"].keys())[0])
    team = state["teams"][team_id]
    assets_df = load_assets()

    st.markdown(
        f'<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;'
        f'letter-spacing:0.1em;color:#00d4ff;margin:0 0 4px;">'
        f'💼 TRADING DESK — {team["emoji"]} {team["name"].upper()}</h1>',
        unsafe_allow_html=True,
    )

    cash = team.get("cash", 0)
    st.markdown(
        f'<div style="font-family:Share Tech Mono,monospace;font-size:0.9rem;'
        f'color:#ffd700;margin-bottom:12px;">💰 Available Cash: <b>${cash:,.0f}</b></div>',
        unsafe_allow_html=True,
    )

    tab_spot, tab_options = st.tabs(["📈 Spot Trading", "⚙️ Options"])

    # ══════════════════════════════════════════════════════
    # SPOT TRADING
    # ══════════════════════════════════════════════════════
    with tab_spot:
        section_title("ORDER TICKET — SPOT")

        all_tickers = assets_df["ticker"].tolist()
        ticker = st.selectbox("Asset", all_tickers, key="spot_ticker")

        live_price = get_price(ticker)
        cat_row = assets_df[assets_df["ticker"] == ticker]
        category = cat_row["category"].iloc[0] if not cat_row.empty else "—"

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Last Price", f"{live_price:,.4f}" if live_price == live_price else "—")
        with col2:
            side = st.selectbox("Side", ["BUY", "SELL"], key="spot_side")
        with col3:
            qty = st.number_input("Quantity", min_value=0.0, step=1.0, value=1.0, key="spot_qty")

        cash_impact = live_price * qty * (-1 if side == "BUY" else 1)
        st.markdown(
            f'<div style="font-family:Share Tech Mono;font-size:0.85rem;'
            f'color:{"#ff3b6b" if side=="BUY" else "#00ff88"};">'
            f'Estimated cash impact: <b>{cash_impact:+,.2f}</b> &nbsp;|&nbsp; '
            f'Cash after: <b>${cash + cash_impact:,.0f}</b></div>',
            unsafe_allow_html=True,
        )

        if st.button("🚀 EXECUTE ORDER", key="spot_exec"):
            if live_price != live_price:
                st.error("Cannot fetch live price.")
            elif side == "BUY" and cash + cash_impact < 0:
                st.error("Insufficient cash.")
            elif side == "SELL":
                held_qty = team["holdings"].get(ticker, {}).get("qty", 0)
                if qty > held_qty:
                    st.error(f"Cannot sell {qty} — only {held_qty} held.")
                else:
                    _execute_spot(state, team_id, ticker, side, qty, live_price)
                    persist_state()
                    st.success(f"✅ SOLD {qty} × {ticker} @ {live_price:,.4f}")
                    st.rerun()
            else:
                _execute_spot(state, team_id, ticker, side, qty, live_price)
                persist_state()
                st.success(f"✅ BOUGHT {qty} × {ticker} @ {live_price:,.4f}")
                st.rerun()

        # ── Current holdings ──
        section_title("CURRENT HOLDINGS")
        holdings = team.get("holdings", {})
        if holdings:
            rows = []
            for t, pos in holdings.items():
                cp = get_price(t)
                unreal = (cp - pos["avg_price"]) * pos["qty"]
                rows.append({
                    "Ticker": t,
                    "Qty": pos["qty"],
                    "Avg Price": f"{pos['avg_price']:,.4f}",
                    "Last Price": f"{cp:,.4f}" if cp == cp else "—",
                    "Mkt Value": f"{cp * pos['qty']:,.0f}" if cp == cp else "—",
                    "Unreal. P&L": f"{unreal:+,.0f}" if cp == cp else "—",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No spot positions.")

    # ══════════════════════════════════════════════════════
    # OPTIONS
    # ══════════════════════════════════════════════════════
    with tab_options:
        st.markdown("""
        <div style="font-family:Share Tech Mono;font-size:0.75rem;color:#94a3b8;
                    background:#0d1117;padding:10px;border-radius:6px;
                    border:1px solid rgba(0,212,255,0.2);margin-bottom:12px;">
        <b style="color:#00d4ff;">European options</b> priced with Black–Scholes.
        Contract multiplier = 100 for equities/ETFs, but 1 for crypto underlyings.
        No naked shorts. BUY requires a future expiry.
        SELL is sell-to-close only.
        </div>
        """, unsafe_allow_html=True)

        section_title("OPTION TICKET")

        col1, col2 = st.columns(2)
        with col1:
            optionable = assets_df[assets_df["category"].isin(
                ["ETF", "Equity", "Crypto", "Forex", "Commodity", "Index"]
            )]["ticker"].tolist()
            opt_ticker = st.selectbox("Underlying", optionable, key="opt_ticker")
            cp = st.selectbox("Type", ["Call (C)", "Put (P)"], key="opt_cp")
            cp_code = "C" if cp.startswith("C") else "P"
            opt_side = st.selectbox("Side", ["BUY", "SELL"], key="opt_side")

        spot = get_price(opt_ticker)
        mult = _get_contract_mult(opt_ticker, assets_df)

        with col2:
            strike = st.number_input("Strike", value=float(spot) if spot == spot else 100.0,
                                     step=max(spot * 0.01 if spot == spot else 1.0, 0.01),
                                     format="%.4f", key="opt_strike")
            min_exp = date.today() + timedelta(days=1)
            expiry = st.date_input("Expiry", value=date(2026, 8, 4),
                                   min_value=min_exp, key="opt_expiry")
            contracts = st.number_input("Contracts", min_value=1, step=1, value=1, key="opt_contracts")
            iv = st.slider("Implied Vol (%)", 5.0, 200.0, 25.0, step=0.5, key="opt_iv") / 100

        if spot == spot:
            ticket = price_option_ticket(spot, strike, expiry, iv, cp_code, mult)
            premium = ticket["premium"]
            premium_per = ticket["premium_per_contract"]
            delta_total = ticket["delta_total"] * contracts
            cash_impact_opt = -premium_per * contracts if opt_side == "BUY" else premium_per * contracts

            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("Premium (per unit)", f"{premium:,.4f}")
            col_b.metric("Premium (per contract)", f"{premium_per:,.2f}")
            col_c.metric("Delta total", f"{delta_total:,.2f}")
            col_d.metric("Cash impact", f"{cash_impact_opt:+,.0f}")

            spot_hedge = -delta_total
            st.markdown(
                f'<div style="font-family:Share Tech Mono;font-size:0.8rem;color:#94a3b8;">'
                f'Contract multiplier for {opt_ticker}: <b>{mult}</b>. '
                f'For delta-neutral hedge, take opposite spot: '
                f'<b style="color:#ffd700;">{spot_hedge:+.2f}</b> {opt_ticker}</div>',
                unsafe_allow_html=True,
            )

            if st.button("⚡ EXECUTE OPTION ORDER", key="opt_exec"):
                if opt_side == "BUY":
                    if cash + cash_impact_opt < 0:
                        st.error("Insufficient cash.")
                    else:
                        _execute_option(state, team_id, opt_ticker, cp_code, strike,
                                        expiry, contracts, mult, premium, iv, "BUY")
                        state["teams"][team_id]["cash"] += cash_impact_opt
                        persist_state()
                        st.success(f"✅ Bought {contracts} × {cp_code} {opt_ticker} {strike:.2f} exp {expiry}")
                        st.rerun()
                else:
                    # Sell-to-close only
                    closed = _close_option(state, team_id, opt_ticker, cp_code, strike,
                                           expiry, contracts, premium)
                    if closed:
                        state["teams"][team_id]["cash"] += cash_impact_opt
                        persist_state()
                        st.success("✅ Option position closed.")
                        st.rerun()
                    else:
                        st.error("No matching long position to close.")
        else:
            st.warning("Cannot fetch spot price for this asset.")

        # ── Open option positions ──
        section_title("OPEN OPTION POSITIONS")
        opts = team.get("options", [])
        if opts:
            rows = []
            for o in opts:
                S = get_price(o["underlying"])
                T = _time_to_expiry(o["expiry"])
                mtm = bs_price(S, strike, T, 0.045, o.get("iv", 0.25), o["cp"]) if S == S else 0
                mtm_val = mtm * o["contract_mult"] * o["qty"]
                unreal = (mtm - o["avg_premium"]) * o["contract_mult"] * o["qty"]
                from utils.options import bs_delta
                delta_t = bs_delta(S, o["strike"], T, 0.045, o.get("iv", 0.25), o["cp"]) * o["contract_mult"] * o["qty"] if S == S else 0
                rows.append({
                    "Underlying": o["underlying"], "C/P": o["cp"],
                    "Strike": f"{o['strike']:,.4f}", "Expiry": o["expiry"],
                    "Qty": o["qty"], "Mult": o["contract_mult"],
                    "Avg Prem": f"{o['avg_premium']:,.4f}",
                    "MtM Prem": f"{mtm:,.4f}",
                    "MtM Value": f"{mtm_val:,.0f}",
                    "Unreal. P&L": f"{unreal:+,.0f}",
                    "Delta Total": f"{delta_t:,.2f}",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No open option positions.")


# ── Execution helpers ─────────────────────────────────────────────────────────

def _execute_spot(state, team_id, ticker, side, qty, price):
    from datetime import datetime
    team = state["teams"][team_id]
    holdings = team.setdefault("holdings", {})
    if side == "BUY":
        if ticker in holdings:
            old_qty = holdings[ticker]["qty"]
            old_avg = holdings[ticker]["avg_price"]
            new_qty = old_qty + qty
            holdings[ticker]["avg_price"] = (old_avg * old_qty + price * qty) / new_qty
            holdings[ticker]["qty"] = new_qty
        else:
            holdings[ticker] = {"qty": qty, "avg_price": price}
        team["cash"] -= price * qty
    else:
        holdings[ticker]["qty"] -= qty
        team["cash"] += price * qty
        if holdings[ticker]["qty"] <= 0:
            del holdings[ticker]

    team.setdefault("trades", []).append({
        "date": str(datetime.utcnow())[:19],
        "type": "SPOT",
        "side": side,
        "ticker": ticker,
        "qty": qty,
        "price": round(price, 4),
        "cash_impact": round(price * qty * (-1 if side == "BUY" else 1), 2),
    })
    # Update portfolio history
    holdings2 = team.get("holdings", {})
    prices2 = {t: get_price(t) for t in holdings2}
    from utils.data import value_portfolio
    val = value_portfolio(team, prices2)
    team.setdefault("portfolio_history", []).append({
        "date": str(datetime.utcnow())[:10],
        "value": val["total"],
    })


def _execute_option(state, team_id, underlying, cp, strike, expiry,
                    qty, mult, premium, iv, side):
    from datetime import datetime
    team = state["teams"][team_id]
    team.setdefault("options", []).append({
        "underlying": underlying, "cp": cp,
        "strike": float(strike), "expiry": str(expiry),
        "qty": qty, "contract_mult": mult,
        "avg_premium": float(premium), "iv": float(iv),
        "opened": str(datetime.utcnow())[:10],
    })
    team.setdefault("trades", []).append({
        "date": str(datetime.utcnow())[:19],
        "type": "OPTION",
        "side": side,
        "ticker": f"{underlying} {cp} {strike:.2f} {expiry}",
        "qty": qty,
        "price": round(premium, 4),
        "cash_impact": round(-premium * mult * qty, 2),
    })


def _close_option(state, team_id, underlying, cp, strike, expiry, qty, premium):
    team = state["teams"][team_id]
    opts = team.get("options", [])
    for i, o in enumerate(opts):
        if (o["underlying"] == underlying and o["cp"] == cp
                and abs(o["strike"] - float(strike)) < 1e-3
                and str(o["expiry"])[:10] == str(expiry)[:10]):
            if o["qty"] >= qty:
                o["qty"] -= qty
                if o["qty"] == 0:
                    opts.pop(i)
                return True
    return False
