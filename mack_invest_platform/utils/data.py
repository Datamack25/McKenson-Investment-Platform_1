# utils/data.py  —  McKenson Asset Management (MAM)  v4.0
"""
Real-time market data via yfinance (15-min delayed).
Game state management, news scraping, portfolio calculations.

v4.0 changes:
  - get_multi_prices: uses fast_info.last_price + previous_close (per ticker)
    for accurate 1D change; falls back to history() if fast_info fails
  - ttl réduit à 60s pour que le P&L se rafraîchisse plus souvent
  - get_price / get_price_change alignés sur même logique
"""
from __future__ import annotations
import json
import math
import glob
from pathlib import Path
from datetime import datetime
from typing import Any

import pandas as pd
import numpy as np
import streamlit as st

try:
    import yfinance as yf
    _YF = True
except ImportError:
    _YF = False

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
DATA_DIR   = ROOT / "data"
STATE_FILE = DATA_DIR / "game_state.json"
INITIAL_CASH = 1_000_000.0

# ── Portfolio strategies catalogue ─────────────────────────────────────────────
STRATEGIES = [
    {"id": "growth",    "name": "Growth",        "emoji": "📈", "desc": "High-growth tech & momentum stocks"},
    {"id": "value",     "name": "Value",          "emoji": "💎", "desc": "Undervalued assets — Graham approach"},
    {"id": "momentum",  "name": "Momentum",       "emoji": "🚀", "desc": "Trend-following across asset classes"},
    {"id": "income",    "name": "Income",         "emoji": "💰", "desc": "Dividends & yield-generating assets"},
    {"id": "macro",     "name": "Global Macro",   "emoji": "🌍", "desc": "Multi-asset macro thematic plays"},
    {"id": "hedging",   "name": "Hedging",        "emoji": "🛡️", "desc": "Options & inverse positions"},
    {"id": "balanced",  "name": "Balanced 60/40", "emoji": "⚖️", "desc": "Classic equity/bond allocation"},
    {"id": "commodity", "name": "Commodities",    "emoji": "🛢️", "desc": "Raw materials & energy exposure"},
    {"id": "crypto",    "name": "Crypto Alpha",   "emoji": "₿",  "desc": "Digital asset basket strategy"},
    {"id": "arbitrage", "name": "Arbitrage",      "emoji": "🔁", "desc": "Market-neutral long/short alpha"},
]

# ── Fallback prices (May 2026 reference — used when yfinance is unavailable) ──
_FB: dict[str, float] = {
    "AAPL": 211.0, "MSFT": 415.0, "NVDA": 875.0, "AMZN": 195.0, "GOOGL": 175.0,
    "META": 520.0, "TSLA": 175.0, "NFLX": 680.0, "ADBE": 480.0, "CRM": 295.0,
    "ORCL": 135.0, "INTC": 22.0, "AMD": 155.0, "QCOM": 170.0,
    "JPM": 210.0, "GS": 490.0, "BAC": 42.0, "MS": 118.0, "BRK-B": 415.0,
    "V": 285.0, "MA": 490.0, "XOM": 118.0, "CVX": 162.0,
    "JNJ": 158.0, "UNH": 530.0, "PFE": 29.0, "LLY": 890.0, "ABBV": 195.0,
    "WMT": 68.0, "KO": 63.0, "PG": 172.0, "MCD": 295.0,
    "MC.PA": 710.0, "AIR.PA": 165.0, "SAN.PA": 52.0, "BNP.PA": 67.0,
    "TTE.PA": 62.0, "OR.PA": 390.0, "SIE.DE": 195.0, "SAP.DE": 210.0,
    "ALV.DE": 295.0, "ASML.AS": 825.0, "NESN.SW": 92.0, "NOVN.SW": 95.0,
    "ROG.SW": 285.0, "AZN.L": 12800.0, "SHEL.L": 2850.0, "HSBA.L": 740.0,
    "9984.T": 9200.0, "6758.T": 2650.0, "7203.T": 3250.0,
    "005930.KS": 72000.0, "0700.HK": 385.0, "BABA": 90.0,
    "RELIANCE.NS": 2950.0, "VALE3.SA": 14.0,
    "GC=F": 2385.0, "SI=F": 32.0, "PL=F": 1050.0, "HG=F": 4.55,
    "CL=F": 81.4, "BZ=F": 85.1, "NG=F": 2.35,
    "ZW=F": 590.0, "ZC=F": 445.0, "ZS=F": 1180.0,
    "BTC-USD": 63450.0, "ETH-USD": 3250.0, "BNB-USD": 610.0, "SOL-USD": 165.0,
    "XRP-USD": 0.62, "ADA-USD": 0.48, "AVAX-USD": 38.0, "DOT-USD": 7.2,
    "EURUSD=X": 1.0812, "GBPUSD=X": 1.2650, "USDJPY=X": 155.40,
    "USDCHF=X": 0.9020, "AUDUSD=X": 0.6580, "USDCAD=X": 1.3650,
    "SPY": 562.0, "QQQ": 480.0, "IWM": 205.0, "VTI": 255.0,
    "EEM": 42.0, "EWJ": 70.0, "GLD": 220.0, "SLV": 29.0, "USO": 75.0,
    "IEF": 94.0, "TLT": 88.0, "HYG": 77.0, "LQD": 108.0, "VNQ": 85.0,
    "ARKK": 52.0, "XLF": 42.0, "XLE": 92.0, "XLV": 145.0,
    "^GSPC": 5620.0, "^IXIC": 17850.0, "^DJI": 40210.0, "^VIX": 16.5,
    "^FCHI": 7932.0, "^GDAXI": 18450.0, "^STOXX50E": 4887.0, "^FTSE": 8320.0,
    "^N225": 38500.0, "^HSI": 18200.0, "^TNX": 4.38,
}

_FB_PCT: dict[str, float] = {
    "AAPL": 0.42, "MSFT": 0.67, "NVDA": 2.30, "AMZN": 1.12, "GOOGL": -0.18,
    "META": 0.88, "TSLA": -1.45, "NFLX": 0.55, "ADBE": -0.33, "CRM": 0.44,
    "JPM": 0.31, "GS": 0.55, "BAC": 0.22, "V": 0.18, "MA": 0.22,
    "XOM": 0.44, "CVX": 0.18, "JNJ": -0.08, "LLY": 1.20, "PFE": -0.62,
    "MC.PA": -0.38, "AIR.PA": 0.92, "SAN.PA": -0.14, "BNP.PA": 0.67,
    "ASML.AS": -0.88, "SAP.DE": 1.10, "SIE.DE": 0.44,
    "GC=F": 0.55, "SI=F": 0.88, "CL=F": -0.73, "BZ=F": -0.61, "NG=F": 1.44,
    "BTC-USD": 1.24, "ETH-USD": 2.10, "SOL-USD": 3.20, "BNB-USD": 0.88,
    "XRP-USD": 0.44, "EURUSD=X": 0.08, "GBPUSD=X": 0.12, "USDJPY=X": -0.22,
    "SPY": 0.42, "QQQ": 0.67, "GLD": 0.55, "TLT": -0.18, "HYG": 0.15,
    "^GSPC": 0.42, "^IXIC": 0.67, "^DJI": 0.31, "^VIX": -2.50,
    "^FCHI": -0.18, "^GDAXI": 0.22, "^STOXX50E": -0.09, "^FTSE": 0.14,
    "^N225": 0.88, "^HSI": -0.44, "^TNX": 0.02,
}


# ══════════════════════════════════════════════════════════════════════════════
#  PRICE FETCHING  (yfinance — real prices, ~15-min delayed)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=60, show_spinner=False)
def get_price(ticker: str) -> float:
    """Single ticker — returns latest real price from yfinance."""
    if not _YF:
        return _FB.get(ticker, 100.0)
    try:
        info = yf.Ticker(ticker).fast_info
        p = float(info.last_price)
        if math.isnan(p) or p <= 0:
            raise ValueError("bad price")
        return p
    except Exception:
        try:
            hist = yf.Ticker(ticker).history(period="2d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
        except Exception:
            pass
        return _FB.get(ticker, 100.0)


@st.cache_data(ttl=60, show_spinner=False)
def get_price_change(ticker: str) -> tuple[float, float]:
    """
    Returns (price, pct_change_vs_prev_close).
    Uses fast_info.last_price + fast_info.previous_close.
    Falls back to history() if fast_info unavailable.
    """
    if not _YF:
        return _FB.get(ticker, 100.0), _FB_PCT.get(ticker, 0.0)
    try:
        info  = yf.Ticker(ticker).fast_info
        price = float(info.last_price)
        prev  = float(info.previous_close)
        if math.isnan(price) or price <= 0:
            raise ValueError("bad price")
        pct = ((price - prev) / prev * 100) if prev > 0 else 0.0
        return price, pct
    except Exception:
        pass
    # Fallback: history
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        if len(hist) >= 2:
            price = float(hist["Close"].iloc[-1])
            prev  = float(hist["Close"].iloc[-2])
            pct   = ((price - prev) / prev * 100) if prev > 0 else 0.0
            return price, pct
        elif len(hist) == 1:
            return float(hist["Close"].iloc[-1]), 0.0
    except Exception:
        pass
    return _FB.get(ticker, 100.0), _FB_PCT.get(ticker, 0.0)


@st.cache_data(ttl=60, show_spinner=False)
def get_multi_prices(tickers: tuple) -> dict[str, tuple[float, float]]:
    """
    Batch fetch (price, pct_1d_change) for multiple tickers.

    Strategy (per ticker, not batch download):
      1. yf.Ticker(tk).fast_info  → last_price + previous_close  (most accurate)
      2. yf.Ticker(tk).history(period="5d") → last 2 closes      (fallback)
      3. Static _FB / _FB_PCT                                      (offline fallback)

    Returns dict[ticker] = (current_price, pct_change_vs_prev_close)
    P&L $ in dashboard = (current_price - avg_entry_price) * qty   ← always live
    1D Var = pct_change_vs_prev_close                               ← separate metric
    """
    result: dict[str, tuple[float, float]] = {}
    if not tickers:
        return result

    if _YF:
        for tk in tickers:
            try:
                info  = yf.Ticker(tk).fast_info
                price = float(info.last_price)
                prev  = float(info.previous_close)
                if math.isnan(price) or price <= 0:
                    raise ValueError("bad price")
                pct = ((price - prev) / prev * 100) if prev > 0 else 0.0
                result[tk] = (price, pct)
                continue
            except Exception:
                pass
            # Fallback: history
            try:
                hist = yf.Ticker(tk).history(period="5d")
                if len(hist) >= 2:
                    price = float(hist["Close"].iloc[-1])
                    prev  = float(hist["Close"].iloc[-2])
                    pct   = ((price - prev) / prev * 100) if prev > 0 else 0.0
                    result[tk] = (price, pct)
                elif len(hist) == 1:
                    result[tk] = (float(hist["Close"].iloc[-1]), 0.0)
            except Exception:
                pass

    # Fill missing with static fallback
    for tk in tickers:
        if tk not in result:
            result[tk] = (_FB.get(tk, 100.0), _FB_PCT.get(tk, 0.0))

    return result


@st.cache_data(ttl=300, show_spinner=False)
def get_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """OHLCV history — real data from yfinance."""
    if not _YF:
        return pd.DataFrame()
    try:
        df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        return df
    except Exception:
        return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
#  ASSET CATALOGUE
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600, show_spinner=False)
def load_assets() -> pd.DataFrame:
    files = sorted(glob.glob(str(DATA_DIR / "assets*.csv")))
    dfs = []
    for f in files:
        try:
            dfs.append(pd.read_csv(f))
        except Exception:
            pass
    if not dfs:
        return pd.DataFrame(columns=[
            "ticker", "name", "category", "subcategory",
            "currency", "exchange", "description", "type"
        ])
    df = pd.concat(dfs, ignore_index=True).drop_duplicates(subset=["ticker"])
    if "type" not in df.columns and "category" in df.columns:
        df["type"] = df["category"]
    elif "category" not in df.columns and "type" in df.columns:
        df["category"] = df["type"]
    elif "category" not in df.columns and "type" not in df.columns:
        df["category"] = "Unknown"
        df["type"] = "Unknown"
    return df.reset_index(drop=True)


# ══════════════════════════════════════════════════════════════════════════════
#  MARKET EVENTS
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300, show_spinner=False)
def load_events() -> pd.DataFrame:
    try:
        df = pd.read_csv(DATA_DIR / "market_events.csv")
        if "active" in df.columns:
            df["active"] = df["active"].astype(str).str.lower().isin(["true", "1", "yes"])
        return df
    except Exception:
        return pd.DataFrame(columns=[
            "event_id", "date", "headline", "category",
            "scope", "impact", "active", "description"
        ])


# ══════════════════════════════════════════════════════════════════════════════
#  TICKER STRIP DATA
# ══════════════════════════════════════════════════════════════════════════════

_STRIP_TICKERS = [
    ("^GSPC", "S&P 500"), ("^IXIC", "NASDAQ"), ("^DJI", "DOW"),
    ("^FCHI", "CAC 40"), ("^GDAXI", "DAX"), ("^FTSE", "FTSE"),
    ("GC=F", "GOLD"), ("CL=F", "WTI"), ("BTC-USD", "BTC"),
    ("ETH-USD", "ETH"), ("EURUSD=X", "EUR/USD"), ("^VIX", "VIX"),
]


@st.cache_data(ttl=60, show_spinner=False)
def get_strip_data() -> list[dict]:
    tickers = tuple(t for t, _ in _STRIP_TICKERS)
    prices  = get_multi_prices(tickers)
    return [
        {"ticker": name, "price": prices.get(sym, (_FB.get(sym, 0), 0))[0],
         "pct":   prices.get(sym, (0, _FB_PCT.get(sym, 0)))[1]}
        for sym, name in _STRIP_TICKERS
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  INDICES BANNER DATA
# ══════════════════════════════════════════════════════════════════════════════

_INDICES_DEF = [
    ("^GSPC",     "S&P 500",     "🇺🇸"),
    ("^IXIC",     "NASDAQ",      "💻"),
    ("^DJI",      "DOW",         "🏭"),
    ("^VIX",      "VIX",         "😱"),
    ("^FCHI",     "CAC 40",      "🇫🇷"),
    ("^GDAXI",    "DAX",         "🇩🇪"),
    ("^STOXX50E", "STOXX 50",    "🇪🇺"),
    ("^FTSE",     "FTSE 100",    "🇬🇧"),
    ("^N225",     "NIKKEI",      "🇯🇵"),
    ("^HSI",      "HANG SENG",   "🇭🇰"),
    ("GC=F",      "GOLD",        "🥇"),
    ("CL=F",      "WTI OIL",     "🛢️"),
    ("BTC-USD",   "BTC",         "₿"),
    ("EURUSD=X",  "EUR/USD",     "💱"),
    ("^TNX",      "US 10Y",      "📊"),
]


@st.cache_data(ttl=60, show_spinner=False)
def get_indices_data() -> list[dict]:
    tickers = tuple(s for s, _, _ in _INDICES_DEF)
    prices  = get_multi_prices(tickers)
    return [
        {
            "symbol": sym, "name": name, "emoji": emoji,
            "price":  prices.get(sym, (_FB.get(sym, 0), 0))[0],
            "pct":    prices.get(sym, (0, _FB_PCT.get(sym, 0)))[1],
        }
        for sym, name, emoji in _INDICES_DEF
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  NEWS
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=600, show_spinner=False)
def fetch_news_headlines(max_items: int = 18) -> list[dict]:
    feeds = [
        ("https://news.google.com/rss/search?q=stock+market+financial&hl=en&gl=US&ceid=US:en", "Markets"),
        ("https://news.google.com/rss/search?q=central+bank+federal+reserve+ECB&hl=en&gl=US&ceid=US:en", "Central Banks"),
        ("https://news.google.com/rss/search?q=geopolitics+war+conflict+sanctions&hl=en&gl=US&ceid=US:en", "Geopolitics"),
        ("https://news.google.com/rss/search?q=oil+gold+commodities&hl=en&gl=US&ceid=US:en", "Commodities"),
        ("https://news.google.com/rss/search?q=bitcoin+crypto+ethereum&hl=en&gl=US&ceid=US:en", "Crypto"),
    ]
    out = []
    try:
        import urllib.request
        from xml.etree import ElementTree as ET
        for url, cat in feeds:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=4) as r:
                    xml = r.read()
                root = ET.fromstring(xml)
                for item in root.findall(".//item")[:4]:
                    title = (item.findtext("title") or "").split(" - ")[0].strip()
                    link  = (item.findtext("link") or "").strip()
                    if title:
                        out.append({"title": title, "category": cat, "link": link})
            except Exception:
                continue
    except Exception:
        pass
    if len(out) < 5:
        out = _static_news()
    return out[:max_items]


def _static_news() -> list[dict]:
    return [
        {"title": "Federal Reserve holds rates at 4.25-4.50% — signals caution on cuts", "category": "Central Banks", "link": ""},
        {"title": "S&P 500 hits new all-time high on AI earnings beat from NVIDIA", "category": "Markets", "link": ""},
        {"title": "ECB signals June rate cut as Eurozone inflation falls to 2.2%", "category": "Central Banks", "link": ""},
        {"title": "Gold surges to $2,420/oz on geopolitical tensions and dollar weakness", "category": "Commodities", "link": ""},
        {"title": "Bitcoin breaks $65,000 — spot ETF inflows hit $3.2B weekly record", "category": "Crypto", "link": ""},
        {"title": "US-China trade talks: semiconductor export controls under scrutiny", "category": "Geopolitics", "link": ""},
        {"title": "OPEC+ maintains production cuts through Q3 2026 — Brent rises", "category": "Commodities", "link": ""},
        {"title": "Eurozone GDP beats at +0.7% Q1 — Germany manufacturing rebounds", "category": "Markets", "link": ""},
        {"title": "IMF revises global growth forecast to 3.4% for 2026", "category": "Markets", "link": ""},
        {"title": "Bank of Japan shifts policy — yen rallies 1.8% vs dollar", "category": "Central Banks", "link": ""},
        {"title": "Middle East tensions push Brent crude above $90 per barrel", "category": "Geopolitics", "link": ""},
        {"title": "US 10-year Treasury yield climbs to 4.5% on strong payrolls data", "category": "Markets", "link": ""},
        {"title": "Ethereum ETF cumulative flows cross $5 billion in 3 months", "category": "Crypto", "link": ""},
        {"title": "LVMH luxury sales rebound on strong China & US demand", "category": "Markets", "link": ""},
        {"title": "Nikkei 225 hits 40,000 as Bank of Japan eases further", "category": "Markets", "link": ""},
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  GAME STATE
# ══════════════════════════════════════════════════════════════════════════════

def _default_portfolios() -> dict:
    ports = {}
    for i, s in enumerate(STRATEGIES):
        pid = f"P{i + 1:02d}"
        ports[pid] = {
            "id":           pid,
            "name":         s["name"],
            "emoji":        s["emoji"],
            "strategy":     s["id"],
            "description":  s["desc"],
            "cash":         INITIAL_CASH,
            "initial_cash": INITIAL_CASH,
            "holdings":     {},
            "options":      [],
            "trades":       [],
            "history":      [],
        }
    return ports


def _default_state() -> dict:
    return {
        "version": "4.0",
        "created": datetime.now().isoformat(),
        "teams": {
            "T01": {"id": "T01", "name": "Alpha Fund",      "emoji": "🦅", "portfolios": _default_portfolios()},
            "T02": {"id": "T02", "name": "Beta Capital",    "emoji": "🐂", "portfolios": _default_portfolios()},
            "T03": {"id": "T03", "name": "Gamma Partners",  "emoji": "🎯", "portfolios": _default_portfolios()},
            "T04": {"id": "T04", "name": "Delta Trading",   "emoji": "🌊", "portfolios": _default_portfolios()},
            "T05": {"id": "T05", "name": "Epsilon AM",      "emoji": "🔥", "portfolios": _default_portfolios()},
        },
    }


def load_state() -> dict:
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return _default_state()


def save_state(state: dict):
    try:
        DATA_DIR.mkdir(exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2, default=str)
    except Exception:
        pass


def get_or_init_state() -> dict:
    if "mam_state" not in st.session_state:
        st.session_state["mam_state"] = load_state()
    return st.session_state["mam_state"]


def persist():
    if "mam_state" in st.session_state:
        save_state(st.session_state["mam_state"])


# ══════════════════════════════════════════════════════════════════════════════
#  PORTFOLIO CALCULATIONS
# ══════════════════════════════════════════════════════════════════════════════

def value_portfolio(portfolio: dict, prices: dict[str, float]) -> dict:
    """
    Compute full portfolio valuation.
    prices dict must contain current prices (floats), not tuples.
    P&L = (current_price - avg_entry_price) * qty  — always live.
    """
    positions = []
    spot_val  = 0.0
    for ticker, pos in portfolio.get("holdings", {}).items():
        qty  = pos.get("qty", 0)
        avg  = pos.get("avg_price", 0.0)
        curr = prices.get(ticker, avg)   # current live price
        mkt  = qty * curr
        cost = qty * avg
        pnl  = mkt - cost                # live unrealised P&L
        pct  = (pnl / cost * 100) if cost else 0.0
        positions.append({
            "ticker": ticker, "qty": qty,
            "avg_price": avg, "current_price": curr,
            "market_value": mkt, "cost_basis": cost,
            "unreal_pnl": pnl, "pnl_pct": pct,
        })
        spot_val += mkt
    cash  = portfolio.get("cash", 0.0)
    total = cash + spot_val
    return {"total": total, "cash": cash,
            "spot_value": spot_val, "positions": positions}


def compute_risk_metrics(returns: "pd.Series") -> dict | None:
    if returns is None or len(returns) < 5:
        return None
    r = returns.dropna()
    if len(r) < 5:
        return None
    ann_vol = float(r.std() * np.sqrt(252))
    ann_ret = float((1 + r.mean()) ** 252 - 1)
    sharpe  = ann_ret / ann_vol if ann_vol > 0 else 0.0
    cum     = (1 + r).cumprod()
    mdd     = float(((cum - cum.cummax()) / cum.cummax()).min())
    var99   = float(r.quantile(0.01))
    cvar99  = float(r[r <= var99].mean()) if (r <= var99).any() else var99
    calmar  = ann_ret / abs(mdd) if mdd else 0.0
    down_r  = r[r < 0]
    sortino = ann_ret / float(down_r.std() * np.sqrt(252)) if len(down_r) > 1 else 0.0
    return {
        "ann_vol":      ann_vol,
        "ann_ret":      ann_ret,
        "sharpe":       sharpe,
        "max_drawdown": mdd,
        "var_99_10d":   var99 * np.sqrt(10),
        "cvar_99_10d":  cvar99 * np.sqrt(10),
        "calmar":       calmar,
        "sortino":      sortino,
    }


# Alias for legacy pages
compute_portfolio_metrics = compute_risk_metrics


def record_trade(portfolio: dict, ticker: str, action: str,
                 qty: float, price: float) -> str:
    """
    Execute buy/sell. Updates holdings & cash in-place.
    price must be the CURRENT live price fetched at trade time — not hardcoded.
    Returns error string or '' on success.
    """
    total = qty * price
    h     = portfolio.setdefault("holdings", {})
    tr    = portfolio.setdefault("trades",   [])

    if action == "BUY":
        if total > portfolio.get("cash", 0) + 0.01:
            return f"Fonds insuffisants (cash: ${portfolio.get('cash', 0):,.0f})"
        portfolio["cash"] -= total
        if ticker in h:
            old_qty = h[ticker]["qty"]
            old_avg = h[ticker]["avg_price"]
            new_qty = old_qty + qty
            h[ticker] = {
                "qty":       new_qty,
                "avg_price": (old_qty * old_avg + qty * price) / new_qty,
            }
        else:
            h[ticker] = {"qty": qty, "avg_price": price}

    elif action == "SELL":
        avail = h.get(ticker, {}).get("qty", 0)
        if avail < qty - 1e-9:
            return f"Position insuffisante ({avail:.4f} disponible, vente demandée: {qty:.4f})"
        portfolio["cash"] = portfolio.get("cash", 0) + total
        h[ticker]["qty"] -= qty
        if h[ticker]["qty"] < 1e-9:
            del h[ticker]
    else:
        return f"Action invalide: {action}"

    tr.append({
        "date":   datetime.now().strftime("%Y-%m-%d %H:%M"),
        "ticker": ticker,
        "action": action,
        "qty":    round(qty, 6),
        "price":  round(price, 6),
        "total":  round(total, 2),
    })
    persist()
    return ""
