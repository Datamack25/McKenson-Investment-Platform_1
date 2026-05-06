"""
Data helpers: yfinance wrappers, state persistence, price cache.
"""
import os
import json
import time
import hashlib
import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st
from datetime import date, datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
STATE_FILE = DATA_DIR / "game_state.json"


# ── Price fetching ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def get_price(ticker: str) -> float:
    """Return latest close price for a ticker."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="2d", interval="1d")
        if hist.empty:
            return float("nan")
        return float(hist["Close"].iloc[-1])
    except Exception:
        return float("nan")


@st.cache_data(ttl=60, show_spinner=False)
def get_ticker_info(ticker: str) -> dict:
    try:
        t = yf.Ticker(ticker)
        info = t.info
        return {
            "name": info.get("longName", ticker),
            "currency": info.get("currency", "USD"),
            "sector": info.get("sector", "—"),
            "market_cap": info.get("marketCap", None),
        }
    except Exception:
        return {"name": ticker, "currency": "USD", "sector": "—", "market_cap": None}


@st.cache_data(ttl=300, show_spinner=False)
def get_history(ticker: str, period="1y", interval="1d") -> pd.DataFrame:
    """Return OHLCV history."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period, interval=interval)
        if hist.empty:
            return pd.DataFrame()
        hist.index = pd.to_datetime(hist.index)
        hist.index = hist.index.tz_localize(None)
        return hist
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def get_multi_prices(tickers: list, period="6mo") -> pd.DataFrame:
    """Return close prices for multiple tickers."""
    try:
        raw = yf.download(tickers, period=period, auto_adjust=True,
                          progress=False, threads=True)
        if isinstance(raw.columns, pd.MultiIndex):
            closes = raw["Close"]
        else:
            closes = raw[["Close"]] if "Close" in raw.columns else raw
        closes = closes.dropna(how="all")
        closes.index = pd.to_datetime(closes.index).tz_localize(None)
        return closes
    except Exception:
        return pd.DataFrame()


def get_ticker_change(ticker: str) -> tuple[float, float]:
    """Return (price, pct_change) for the ticker."""
    try:
        hist = yf.Ticker(ticker).history(period="5d", interval="1d")
        if len(hist) < 2:
            return float("nan"), 0.0
        price = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2])
        return price, (price - prev) / prev * 100
    except Exception:
        return float("nan"), 0.0


# ── Ticker strip data ──────────────────────────────────────────────────────────

STRIP_TICKERS = [
    "SPY", "AAPL", "MSFT", "NVDA", "BTC-USD", "ETH-USD",
    "^FCHI", "^GSPC", "GC=F", "CL=F", "0700.HK", "1299.HK",
    "EURUSD=X", "JPY=X",
]


@st.cache_data(ttl=60, show_spinner=False)
def get_strip_data() -> list[dict]:
    """Return list of {ticker, price, pct} for the ticker strip."""
    results = []
    for t in STRIP_TICKERS:
        price, pct = get_ticker_change(t)
        results.append({"ticker": t, "price": price, "pct": pct})
    return results


# ── Game state persistence ─────────────────────────────────────────────────────

def _default_state() -> dict:
    teams_df = pd.read_csv(DATA_DIR / "teams.csv")
    teams = {}
    for _, row in teams_df.iterrows():
        teams[row["team_id"]] = {
            "name": row["name"],
            "emoji": row["emoji"],
            "cash": float(row["initial_cash"]),
            "holdings": {},      # {ticker: {"qty": ..., "avg_price": ...}}
            "options": [],       # list of option position dicts
            "trades": [],        # trade log
            "portfolio_history": [],   # [{date, value}]
            "members": [],
        }
    return {
        "teams": teams,
        "events": [],
        "last_updated": str(datetime.utcnow()),
        "admin_password": "eslsca2026",
    }


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    state = _default_state()
    save_state(state)
    return state


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = str(datetime.utcnow())
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def get_or_init_state() -> dict:
    if "game_state" not in st.session_state:
        st.session_state["game_state"] = load_state()
    return st.session_state["game_state"]


def persist_state():
    state = st.session_state.get("game_state", {})
    save_state(state)


# ── Portfolio valuation ────────────────────────────────────────────────────────

def value_portfolio(team_data: dict, prices: dict) -> dict:
    """
    Given team dict and {ticker: price}, compute total portfolio value,
    unrealised P&L, weight per asset.
    """
    holdings = team_data.get("holdings", {})
    cash = team_data.get("cash", 0.0)
    spot_value = 0.0
    positions = []
    for ticker, pos in holdings.items():
        qty = pos.get("qty", 0)
        avg = pos.get("avg_price", 0)
        price = prices.get(ticker, avg)
        mkt_val = qty * price
        unreal = (price - avg) * qty
        spot_value += mkt_val
        positions.append({
            "ticker": ticker,
            "qty": qty,
            "avg_price": avg,
            "current_price": price,
            "market_value": mkt_val,
            "unreal_pnl": unreal,
            "pnl_pct": (price - avg) / avg * 100 if avg > 0 else 0,
        })
    total = cash + spot_value
    return {
        "total": total,
        "cash": cash,
        "spot_value": spot_value,
        "positions": positions,
    }


def compute_portfolio_metrics(returns_series: pd.Series) -> dict:
    """Annualised metrics from a series of daily portfolio returns."""
    if returns_series.empty or len(returns_series) < 2:
        return {}
    ann_ret = returns_series.mean() * 252
    ann_vol = returns_series.std() * np.sqrt(252)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0
    cum = (1 + returns_series).cumprod()
    roll_max = cum.cummax()
    dd = (cum - roll_max) / roll_max
    max_dd = dd.min()
    from scipy.stats import norm
    var_99_1d = -returns_series.quantile(0.01)
    cvar_99_1d = -returns_series[returns_series <= returns_series.quantile(0.01)].mean()
    return {
        "ann_return": ann_ret,
        "ann_vol": ann_vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "var_99_10d": var_99_1d * np.sqrt(10),
        "cvar_99_10d": cvar_99_1d * np.sqrt(10),
    }


def load_assets() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "assets.csv")


def load_events() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "market_events.csv")
