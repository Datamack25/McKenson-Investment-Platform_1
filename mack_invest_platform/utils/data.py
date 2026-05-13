# utils/data.py  —  MAM v4.1
"""
- State management (persist/load JSON)
- Asset loading depuis assets.csv (colonnes: ticker, name, category, contract_mult, currency)
- Price fetching via yfinance (cache 30s — quasi temps réel)
- P&L = (last - avg_cost) * qty  — recalculé à chaque rafraîchissement
- record_trade : VWAP sur achats successifs
- get_contract_mult / get_currency : utilisés par le module options
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ── Paths ─────────────────────────────────────────────────────────────────────
_HERE       = Path(__file__).parent.parent
STATE_FILE  = _HERE / "data" / "state.json"
ASSETS_FILE = _HERE / "assets.csv"

# ══════════════════════════════════════════════════════════════════════════════
#  STATE
# ══════════════════════════════════════════════════════════════════════════════

def get_or_init_state() -> dict:
    if "mam_state" not in st.session_state:
        loaded = _load_state()
        st.session_state["mam_state"] = loaded if loaded else _default_state()
    return st.session_state["mam_state"]


def persist():
    state = st.session_state.get("mam_state", {})
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, default=str)
    except Exception as e:
        st.warning(f"Sauvegarde échouée : {e}")


def _load_state() -> dict | None:
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _default_state() -> dict:
    return {
        "teams": {},
        "global_settings": {"base_currency": "USD", "risk_free_rate": 0.0425},
    }


# ══════════════════════════════════════════════════════════════════════════════
#  ASSET LOADING
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def load_assets() -> pd.DataFrame:
    """
    Charge assets.csv.
    Colonnes attendues: ticker, name, category, contract_mult, currency
    """
    paths = [ASSETS_FILE, Path("assets.csv"), Path("data/assets.csv")]
    for p in paths:
        if p.exists():
            try:
                df = pd.read_csv(p)
                df["category"]      = df.get("category",      pd.Series()).fillna("Equity")
                df["contract_mult"] = pd.to_numeric(
                    df.get("contract_mult", pd.Series()), errors="coerce"
                ).fillna(100).astype(int)
                df["currency"]      = df.get("currency", pd.Series()).fillna("USD")
                return df
            except Exception:
                pass

    # Fallback minimal si assets.csv absent
    return pd.DataFrame([
        {"ticker": "AAPL",    "name": "Apple Inc.",       "category": "Equity",    "contract_mult": 100,    "currency": "USD"},
        {"ticker": "MSFT",    "name": "Microsoft Corp.",  "category": "Equity",    "contract_mult": 100,    "currency": "USD"},
        {"ticker": "NVDA",    "name": "NVIDIA Corp.",     "category": "Equity",    "contract_mult": 100,    "currency": "USD"},
        {"ticker": "BTC-USD", "name": "Bitcoin USD",      "category": "Crypto",    "contract_mult": 1,      "currency": "USD"},
        {"ticker": "ETH-USD", "name": "Ethereum USD",     "category": "Crypto",    "contract_mult": 1,      "currency": "USD"},
        {"ticker": "GC=F",    "name": "Gold Futures",     "category": "Commodity", "contract_mult": 100,    "currency": "USD"},
        {"ticker": "CL=F",    "name": "WTI Crude Oil",    "category": "Commodity", "contract_mult": 100,    "currency": "USD"},
        {"ticker": "EURUSD=X","name": "EUR/USD",          "category": "Forex",     "contract_mult": 100000, "currency": "USD"},
        {"ticker": "QQQ",     "name": "Invesco QQQ",      "category": "ETF",       "contract_mult": 100,    "currency": "USD"},
        {"ticker": "SPY",     "name": "SPDR S&P 500",     "category": "ETF",       "contract_mult": 100,    "currency": "USD"},
    ])


def get_contract_mult(ticker: str) -> int:
    """Retourne le contract_mult depuis assets.csv."""
    df = load_assets()
    row = df[df["ticker"] == ticker]
    if not row.empty:
        return int(row.iloc[0]["contract_mult"])
    # Défauts heuristiques
    if any(x in ticker for x in ["=X", "GBP=", "JPY="]):
        return 100_000
    if ticker.endswith("-USD"):
        return 1
    return 100


def get_currency(ticker: str) -> str:
    """Retourne la devise depuis assets.csv."""
    df = load_assets()
    row = df[df["ticker"] == ticker]
    if not row.empty:
        return str(row.iloc[0]["currency"])
    return "USD"


# ══════════════════════════════════════════════════════════════════════════════
#  PRICE FETCHING  (cache court = quasi temps réel)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=30)
def get_price(ticker: str) -> float:
    """Dernier prix disponible."""
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).fast_info
        for attr in ("last_price", "regular_market_price", "previous_close"):
            px = getattr(info, attr, None)
            if px and float(px) > 0:
                return float(px)
        hist = yf.Ticker(ticker).history(period="2d", auto_adjust=True)
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return 0.0


@st.cache_data(ttl=30)
def get_price_change(ticker: str) -> tuple[float, float]:
    """(last_price, pct_change_vs_prev_close)"""
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).fast_info
        curr = getattr(info, "last_price", None) or getattr(info, "regular_market_price", None)
        prev = getattr(info, "previous_close", None)
        if curr and prev and float(prev) > 0:
            curr, prev = float(curr), float(prev)
            return curr, (curr - prev) / prev * 100
        # Fallback historique
        hist = yf.Ticker(ticker).history(period="5d", auto_adjust=True)
        col  = hist["Close"].dropna()
        if len(col) >= 2:
            c0, c1 = float(col.iloc[-2]), float(col.iloc[-1])
            return c1, (c1 - c0) / c0 * 100 if c0 > 0 else 0.0
        if len(col) == 1:
            return float(col.iloc[0]), 0.0
    except Exception:
        pass
    return 0.0, 0.0


@st.cache_data(ttl=30)
def get_multi_prices(tickers: tuple) -> dict[str, tuple[float, float]]:
    """
    Télécharge en batch (plus rapide).
    Retourne {ticker: (last_price, pct_1d)}.
    Cache 30 s → prix se mettent à jour automatiquement.
    """
    if not tickers:
        return {}

    results: dict[str, tuple[float, float]] = {}
    try:
        import yfinance as yf
        raw = yf.download(
            list(tickers), period="5d", interval="1d",
            auto_adjust=True, progress=False, threads=True,
        )
        if raw.empty:
            raise ValueError("empty response")

        close = raw["Close"] if "Close" in raw.columns else raw
        if isinstance(close, pd.Series):
            close = close.to_frame(name=tickers[0])

        for tk in tickers:
            try:
                if tk not in close.columns:
                    results[tk] = (0.0, 0.0)
                    continue
                col = close[tk].dropna()
                if len(col) >= 2:
                    c0, c1 = float(col.iloc[-2]), float(col.iloc[-1])
                    results[tk] = (c1, (c1 - c0) / c0 * 100 if c0 > 0 else 0.0)
                elif len(col) == 1:
                    results[tk] = (float(col.iloc[0]), 0.0)
                else:
                    results[tk] = (0.0, 0.0)
            except Exception:
                results[tk] = (0.0, 0.0)

    except Exception:
        # Fallback individuel
        for tk in tickers:
            try:
                results[tk] = get_price_change(tk)
            except Exception:
                results[tk] = (0.0, 0.0)

    return results


@st.cache_data(ttl=300)
def get_history(ticker: str, period: str = "1mo") -> pd.DataFrame:
    try:
        import yfinance as yf
        return yf.Ticker(ticker).history(period=period, auto_adjust=True)
    except Exception:
        return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
#  PORTFOLIO VALUATION
# ══════════════════════════════════════════════════════════════════════════════

def value_portfolio(port: dict) -> dict:
    """
    Mark-to-market complet.
    unreal_pnl = (last_price - avg_cost) * qty   ← recalculé à chaque appel
    """
    holdings = port.get("holdings", {})
    cash     = port.get("cash", 0.0)

    if not holdings:
        return dict(
            total_value=cash, cash=cash, mkt_value=0.0,
            total_pnl=0.0, total_cost=0.0, pnl_pct=0.0, positions=[],
        )

    prices     = get_multi_prices(tuple(holdings.keys()))
    total_mkt  = 0.0
    total_cost = 0.0
    positions  = []

    for tk, pos in holdings.items():
        qty       = pos.get("qty", 0.0)
        avg       = pos.get("avg_price", 0.0)
        last, pct = prices.get(tk, (avg, 0.0))

        mkt_val    = qty * last
        cost_val   = qty * avg
        unreal_pnl = mkt_val - cost_val   # ← jamais statique

        total_mkt  += mkt_val
        total_cost += cost_val
        positions.append(dict(
            ticker=tk, qty=qty, avg_price=avg, last=last,
            pct_1d=pct, mkt_value=mkt_val, cost=cost_val,
            unreal_pnl=unreal_pnl,
            return_mid=unreal_pnl / cost_val if cost_val > 0 else 0.0,
        ))

    total_pnl = total_mkt - total_cost
    return dict(
        total_value=cash + total_mkt,
        cash=cash,
        mkt_value=total_mkt,
        total_pnl=total_pnl,
        total_cost=total_cost,
        pnl_pct=total_pnl / total_cost * 100 if total_cost > 0 else 0.0,
        positions=positions,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  TRADE RECORDING
# ══════════════════════════════════════════════════════════════════════════════

def record_trade(port: dict, ticker: str, action: str,
                 qty: float, price: float) -> str | None:
    """
    BUY  → calcule VWAP avg_price, débite cash
    SELL → crédite cash, retire position si qty épuisée
    Retourne message d'erreur (str) ou None si succès.
    """
    holdings = port.setdefault("holdings", {})
    cash     = port.get("cash", 0.0)
    total    = qty * price

    if action == "BUY":
        if total > cash + 0.01:
            return f"Fonds insuffisants — cash ${cash:,.2f}, ordre ${total:,.2f}"
        if ticker in holdings:
            old_qty = holdings[ticker]["qty"]
            old_avg = holdings[ticker]["avg_price"]
            new_qty = old_qty + qty
            holdings[ticker] = {
                "qty":       new_qty,
                "avg_price": (old_qty * old_avg + qty * price) / new_qty,  # VWAP
            }
        else:
            holdings[ticker] = {"qty": qty, "avg_price": price}
        port["cash"] = cash - total

    elif action == "SELL":
        if ticker not in holdings:
            return f"Pas de position ouverte sur {ticker}"
        held = holdings[ticker]["qty"]
        if qty > held + 1e-8:
            return f"Quantité insuffisante ({held:,.4f} disponible)"
        port["cash"] = cash + total
        remaining = held - qty
        if remaining < 1e-8:
            del holdings[ticker]
        else:
            holdings[ticker]["qty"] = remaining
            # avg_price inchangé sur vente partielle
    else:
        return f"Action inconnue : {action}"

    # Journal
    port.setdefault("trades", []).append(dict(
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        ticker=ticker, action=action,
        qty=round(qty, 6), price=round(price, 6), total=round(total, 2),
    ))
    persist()
    return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def pnl_cell(value: float) -> str:
    """HTML coloré pour affichage P&L inline."""
    color = "#00ff88" if value > 0 else ("#ff3b6b" if value < 0 else "#94a3b8")
    sign  = "+" if value > 0 else ""
    return f'<span style="color:{color};font-weight:bold;">{sign}{value:,.2f}</span>'


def metric_row(items: list[tuple[str, str, str]]) -> None:
    """
    Affiche une ligne de métriques.
    items = [(label, value, color), ...]
    """
    cols = st.columns(len(items))
    for col, (lbl, val, col_c) in zip(cols, items):
        col.markdown(
            f'<div style="background:rgba(0,10,25,.6);border:1px solid rgba(0,212,255,.12);'
            f'border-radius:7px;padding:10px 12px;">'
            f'<div style="font-family:Rajdhani;font-size:.62rem;color:#475569;'
            f'letter-spacing:.1em;text-transform:uppercase;">{lbl}</div>'
            f'<div style="font-family:Share Tech Mono;font-size:1rem;'
            f'color:{col_c};font-weight:bold;margin-top:2px;">{val}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
