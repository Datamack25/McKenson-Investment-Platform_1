# utils/data.py  —  MAM v3.3  PERSISTENT STORAGE
"""
SOLUTION PERSISTANCE :
  Streamlit Cloud efface le filesystem à chaque redémarrage.
  On utilise st.session_state comme cache runtime ET on encode
  l'état en base64 dans un st.query_params pour survivre aux
  rechargements de page.

  Pour une vraie persistance cross-session (entre jours/weekends),
  la solution recommandée est d'ajouter dans secrets.toml :
    [storage]
    backend = "local"   # ou "none" si pas de secrets configurés

  Sans secrets configurés, la plateforme fonctionne normalement
  pendant la session mais repart de zéro si Streamlit Cloud redémarre.

  POUR PERSISTANCE RÉELLE : voir _save_to_secrets() / _load_from_secrets()
  qui utilisent les Streamlit Secrets comme stockage JSON encodé.
"""
from __future__ import annotations
import json
import math
import glob
import base64
import zlib
from pathlib import Path
from datetime import datetime

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

STRATEGIES = [
    {"id":"growth",    "name":"Growth",        "emoji":"📈","desc":"High-growth tech & momentum stocks"},
    {"id":"value",     "name":"Value",          "emoji":"💎","desc":"Undervalued assets — Graham approach"},
    {"id":"momentum",  "name":"Momentum",       "emoji":"🚀","desc":"Trend-following across asset classes"},
    {"id":"income",    "name":"Income",         "emoji":"💰","desc":"Dividends & yield-generating assets"},
    {"id":"macro",     "name":"Global Macro",   "emoji":"🌍","desc":"Multi-asset macro thematic plays"},
    {"id":"hedging",   "name":"Hedging",        "emoji":"🛡️","desc":"Options & inverse positions"},
    {"id":"balanced",  "name":"Balanced 60/40", "emoji":"⚖️","desc":"Classic equity/bond allocation"},
    {"id":"commodity", "name":"Commodities",    "emoji":"🛢️","desc":"Raw materials & energy exposure"},
    {"id":"crypto",    "name":"Crypto Alpha",   "emoji":"₿", "desc":"Digital asset basket strategy"},
    {"id":"arbitrage", "name":"Arbitrage",      "emoji":"🔁","desc":"Market-neutral long/short alpha"},
]

_FB: dict[str,float] = {
    "AAPL":211.0,"MSFT":415.0,"NVDA":875.0,"AMZN":195.0,"GOOGL":175.0,
    "META":520.0,"TSLA":175.0,"NFLX":680.0,"ADBE":480.0,"CRM":295.0,
    "ORCL":135.0,"INTC":22.0,"AMD":155.0,"QCOM":170.0,
    "JPM":210.0,"GS":490.0,"BAC":42.0,"MS":118.0,"BRK-B":415.0,
    "V":285.0,"MA":490.0,"XOM":118.0,"CVX":162.0,
    "JNJ":158.0,"UNH":530.0,"PFE":29.0,"LLY":890.0,"ABBV":195.0,
    "WMT":68.0,"KO":63.0,"PG":172.0,"MCD":295.0,
    "MC.PA":710.0,"AIR.PA":165.0,"SAN.PA":52.0,"BNP.PA":67.0,
    "TTE.PA":62.0,"OR.PA":390.0,"SIE.DE":195.0,"SAP.DE":210.0,
    "GC=F":2385.0,"SI=F":32.0,"CL=F":81.4,"BZ=F":85.1,"NG=F":2.35,
    "BTC-USD":63450.0,"ETH-USD":3250.0,"BNB-USD":610.0,"SOL-USD":165.0,
    "XRP-USD":0.62,"ADA-USD":0.48,
    "EURUSD=X":1.0812,"GBPUSD=X":1.2650,"USDJPY=X":155.40,"USDCHF=X":0.9020,
    "SPY":562.0,"QQQ":480.0,"IWM":205.0,"VTI":255.0,
    "GLD":220.0,"TLT":88.0,"HYG":77.0,"LQD":108.0,
    "^GSPC":5620.0,"^IXIC":17850.0,"^DJI":40210.0,"^VIX":16.5,
    "^FCHI":7932.0,"^GDAXI":18450.0,"^STOXX50E":4887.0,"^FTSE":8320.0,
    "^N225":38500.0,"^HSI":18200.0,"^TNX":4.38,
}
_FB_PCT: dict[str,float] = {
    "AAPL":0.42,"MSFT":0.67,"NVDA":2.30,"AMZN":1.12,"GOOGL":-0.18,
    "META":0.88,"TSLA":-1.45,"GC=F":0.55,"CL=F":-0.73,
    "BTC-USD":1.24,"ETH-USD":2.10,"SOL-USD":3.20,
    "EURUSD=X":0.08,"SPY":0.42,"QQQ":0.67,"GLD":0.55,"TLT":-0.18,
    "^GSPC":0.42,"^IXIC":0.67,"^DJI":0.31,"^VIX":-2.50,
    "^FCHI":-0.18,"^GDAXI":0.22,"^FTSE":0.14,"^N225":0.88,
}


# ══════════════════════════════════════════════════════════════════════════════
#  PRICE FETCHING
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=180, show_spinner=False)
def get_price(ticker: str) -> float:
    if not _YF:
        return _FB.get(ticker, 100.0)
    try:
        p = float(yf.Ticker(ticker).fast_info.last_price)
        if math.isnan(p) or p <= 0: raise ValueError
        return p
    except Exception:
        return _FB.get(ticker, 100.0)


@st.cache_data(ttl=180, show_spinner=False)
def get_price_change(ticker: str) -> tuple[float,float]:
    if not _YF:
        return _FB.get(ticker,100.0), _FB_PCT.get(ticker,0.0)
    try:
        info  = yf.Ticker(ticker).fast_info
        price = float(info.last_price)
        prev  = float(info.previous_close)
        if math.isnan(price) or price<=0: raise ValueError
        return price, (price-prev)/prev*100 if prev>0 else 0.0
    except Exception:
        return _FB.get(ticker,100.0), _FB_PCT.get(ticker,0.0)


@st.cache_data(ttl=180, show_spinner=False)
def get_multi_prices(tickers: tuple) -> dict[str,tuple[float,float]]:
    result: dict[str,tuple[float,float]] = {}
    if not tickers: return result
    if _YF:
        try:
            raw = yf.download(" ".join(tickers), period="5d",
                              auto_adjust=True, progress=False, threads=True)
            closes = raw.get("Close", pd.DataFrame())
            if not closes.empty:
                if isinstance(closes, pd.Series):
                    closes = closes.to_frame(name=tickers[0])
                for t in tickers:
                    if t in closes.columns:
                        s = closes[t].dropna()
                        if len(s)>=2:
                            p,prv = float(s.iloc[-1]),float(s.iloc[-2])
                            result[t] = (p,(p-prv)/prv*100 if prv else 0.0)
                        elif len(s)==1:
                            result[t] = (float(s.iloc[-1]),0.0)
        except Exception:
            pass
    for t in tickers:
        if t not in result:
            result[t] = (_FB.get(t,100.0), _FB_PCT.get(t,0.0))
    return result


@st.cache_data(ttl=300, show_spinner=False)
def get_history(ticker: str, period: str="1y") -> pd.DataFrame:
    if not _YF: return pd.DataFrame()
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
    files = sorted(glob.glob(str(DATA_DIR/"assets*.csv")))
    dfs = []
    for f in files:
        try: dfs.append(pd.read_csv(f))
        except Exception: pass
    if not dfs:
        return pd.DataFrame(columns=["ticker","name","category","subcategory",
                                      "currency","exchange","description","type"])
    df = pd.concat(dfs, ignore_index=True).drop_duplicates(subset=["ticker"])
    if "type" not in df.columns and "category" in df.columns:
        df["type"] = df["category"]
    elif "category" not in df.columns and "type" in df.columns:
        df["category"] = df["type"]
    elif "category" not in df.columns and "type" not in df.columns:
        df["category"] = "Unknown"; df["type"] = "Unknown"
    return df.reset_index(drop=True)


@st.cache_data(ttl=300, show_spinner=False)
def load_events() -> pd.DataFrame:
    try:
        df = pd.read_csv(DATA_DIR/"market_events.csv")
        if "active" in df.columns:
            df["active"] = df["active"].astype(str).str.lower().isin(["true","1","yes"])
        return df
    except Exception:
        return pd.DataFrame(columns=["event_id","date","headline","category",
                                      "scope","impact","active","description"])


# ══════════════════════════════════════════════════════════════════════════════
#  TICKER STRIP / INDICES
# ══════════════════════════════════════════════════════════════════════════════

_STRIP_TICKERS = [
    ("^GSPC","S&P 500"),("^IXIC","NASDAQ"),("^DJI","DOW"),
    ("^FCHI","CAC 40"),("^GDAXI","DAX"),("^FTSE","FTSE"),
    ("GC=F","GOLD"),("CL=F","WTI"),("BTC-USD","BTC"),
    ("ETH-USD","ETH"),("EURUSD=X","EUR/USD"),("^VIX","VIX"),
]
_INDICES_DEF = [
    ("^GSPC","S&P 500","🇺🇸"),("^IXIC","NASDAQ","💻"),("^DJI","DOW","🏭"),
    ("^VIX","VIX","😱"),("^FCHI","CAC 40","🇫🇷"),("^GDAXI","DAX","🇩🇪"),
    ("^STOXX50E","STOXX 50","🇪🇺"),("^FTSE","FTSE 100","🇬🇧"),
    ("^N225","NIKKEI","🇯🇵"),("^HSI","HANG SENG","🇭🇰"),
    ("GC=F","GOLD","🥇"),("CL=F","WTI OIL","🛢️"),
    ("BTC-USD","BTC","₿"),("EURUSD=X","EUR/USD","💱"),("^TNX","US 10Y","📊"),
]


@st.cache_data(ttl=180, show_spinner=False)
def get_strip_data() -> list[dict]:
    tickers = tuple(t for t,_ in _STRIP_TICKERS)
    prices  = get_multi_prices(tickers)
    return [{"ticker":name,
             "price": prices.get(sym,(_FB.get(sym,0),0))[0],
             "pct":   prices.get(sym,(0,_FB_PCT.get(sym,0)))[1]}
            for sym,name in _STRIP_TICKERS]


@st.cache_data(ttl=180, show_spinner=False)
def get_indices_data() -> list[dict]:
    tickers = tuple(s for s,_,_ in _INDICES_DEF)
    prices  = get_multi_prices(tickers)
    return [{"symbol":sym,"name":name,"emoji":emoji,
             "price": prices.get(sym,(_FB.get(sym,0),0))[0],
             "pct":   prices.get(sym,(0,_FB_PCT.get(sym,0)))[1]}
            for sym,name,emoji in _INDICES_DEF]


@st.cache_data(ttl=600, show_spinner=False)
def fetch_news_headlines(max_items: int=18) -> list[dict]:
    feeds = [
        ("https://news.google.com/rss/search?q=stock+market+financial&hl=en&gl=US&ceid=US:en","Markets"),
        ("https://news.google.com/rss/search?q=central+bank+federal+reserve+ECB&hl=en&gl=US&ceid=US:en","Central Banks"),
        ("https://news.google.com/rss/search?q=geopolitics+war+conflict&hl=en&gl=US&ceid=US:en","Geopolitics"),
        ("https://news.google.com/rss/search?q=oil+gold+commodities&hl=en&gl=US&ceid=US:en","Commodities"),
        ("https://news.google.com/rss/search?q=bitcoin+crypto+ethereum&hl=en&gl=US&ceid=US:en","Crypto"),
    ]
    out = []
    try:
        import urllib.request
        from xml.etree import ElementTree as ET
        for url,cat in feeds:
            try:
                req = urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
                with urllib.request.urlopen(req,timeout=4) as r: xml=r.read()
                root = ET.fromstring(xml)
                for item in root.findall(".//item")[:4]:
                    title=(item.findtext("title") or "").split(" - ")[0].strip()
                    if title: out.append({"title":title,"category":cat,"link":""})
            except Exception: continue
    except Exception: pass
    if len(out)<5: out=_static_news()
    return out[:max_items]

def _static_news() -> list[dict]:
    return [
        {"title":"Federal Reserve holds rates at 4.25-4.50%","category":"Central Banks","link":""},
        {"title":"S&P 500 hits new all-time high on AI earnings beat","category":"Markets","link":""},
        {"title":"ECB signals June rate cut as Eurozone inflation falls","category":"Central Banks","link":""},
        {"title":"Gold surges to $2,420/oz on geopolitical tensions","category":"Commodities","link":""},
        {"title":"Bitcoin breaks $65,000 — spot ETF inflows hit record","category":"Crypto","link":""},
        {"title":"OPEC+ maintains production cuts through Q3 2026","category":"Commodities","link":""},
        {"title":"IMF revises global growth forecast to 3.4%","category":"Markets","link":""},
        {"title":"Bank of Japan shifts policy — yen rallies 1.8%","category":"Central Banks","link":""},
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  PERSISTANCE — SOLUTION MULTI-COUCHE
#
#  Couche 1 (runtime)   : st.session_state["mam_state"]
#  Couche 2 (fichier)   : data/game_state.json  (fonctionne en local)
#  Couche 3 (Secrets)   : st.secrets["game_state_b64"]  (survit aux redémarrages Cloud)
#
#  Ordre de chargement : Secrets → fichier → défaut vide
#  Ordre de sauvegarde : fichier + Secrets (si disponible)
# ══════════════════════════════════════════════════════════════════════════════

def _encode_state(state: dict) -> str:
    """Compresse et encode l'état en base64 pour stockage dans les secrets."""
    raw = json.dumps(state, default=str).encode("utf-8")
    return base64.b64encode(zlib.compress(raw, level=6)).decode("ascii")


def _decode_state(b64: str) -> dict:
    """Décode et décompresse un état depuis base64."""
    raw = zlib.decompress(base64.b64decode(b64.encode("ascii")))
    return json.loads(raw.decode("utf-8"))


def _load_from_secrets() -> dict | None:
    """Tente de charger l'état depuis les Streamlit Secrets."""
    try:
        b64 = st.secrets.get("game_state_b64", "")
        if b64:
            state = _decode_state(b64)
            if state.get("teams"):
                return state
    except Exception:
        pass
    return None


def _save_to_secrets_instruction(state: dict):
    """
    Streamlit Secrets ne peut pas être écrit programmatiquement depuis l'app.
    À la place, on affiche l'instruction dans la sidebar admin si l'état a changé.
    On stocke également la clé encodée dans session_state pour affichage admin.
    """
    try:
        st.session_state["_state_b64"] = _encode_state(state)
    except Exception:
        pass


def _default_state() -> dict:
    return {
        "version": "3.3",
        "created": datetime.now().isoformat(),
        "teams": {},
    }


def load_state() -> dict:
    """
    Chargement multi-couche :
    1. Streamlit Secrets (game_state_b64) — survit aux redémarrages
    2. Fichier local game_state.json     — fonctionne en local / dev
    3. État par défaut vide
    """
    # Couche 1 : Secrets Streamlit
    from_secrets = _load_from_secrets()
    if from_secrets:
        return from_secrets

    # Couche 2 : fichier local
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                state = json.load(f)
            if state.get("teams"):
                return state
    except Exception:
        pass

    # Couche 3 : défaut
    return _default_state()


def save_state(state: dict):
    """
    Sauvegarde multi-couche :
    1. Toujours dans le fichier local (dev / self-hosted)
    2. Encode en base64 pour affichage dans Admin (copier dans Secrets)
    """
    # Fichier local
    try:
        DATA_DIR.mkdir(exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2, default=str)
    except Exception:
        pass

    # Encodage pour admin panel
    _save_to_secrets_instruction(state)


def get_or_init_state() -> dict:
    if "mam_state" not in st.session_state:
        st.session_state["mam_state"] = load_state()
    return st.session_state["mam_state"]


def persist():
    """Sauvegarde l'état courant (fichier + encodage secrets)."""
    state = st.session_state.get("mam_state", {})
    if state:
        save_state(state)


# ══════════════════════════════════════════════════════════════════════════════
#  PORTFOLIO CALCULATIONS
# ══════════════════════════════════════════════════════════════════════════════

def value_portfolio(portfolio: dict, prices: dict) -> dict:
    positions = []
    spot_val  = 0.0
    for ticker, pos in portfolio.get("holdings", {}).items():
        qty  = pos.get("qty", 0)
        avg  = pos.get("avg_price", 0.0)
        raw  = prices.get(ticker, avg)
        curr = raw[0] if isinstance(raw,(list,tuple)) else float(raw)
        if not curr or curr!=curr or curr<=0: curr=avg
        mkt  = qty*curr; cost=qty*avg; pnl=mkt-cost
        positions.append({
            "ticker":ticker,"qty":qty,"avg_price":avg,"current_price":curr,
            "market_value":mkt,"cost_basis":cost,
            "unreal_pnl":pnl,"unrealized_pnl":pnl,
            "pnl_pct":(pnl/cost*100) if cost else 0.0,
        })
        spot_val += mkt
    cash  = portfolio.get("cash", 0.0)
    return {"total":cash+spot_val,"cash":cash,"spot_value":spot_val,"positions":positions}


def compute_risk_metrics(returns: "pd.Series") -> dict | None:
    if returns is None or len(returns)<5: return None
    r = returns.dropna()
    if len(r)<5: return None
    ann_vol = float(r.std()*np.sqrt(252))
    ann_ret = float((1+r.mean())**252-1)
    sharpe  = ann_ret/ann_vol if ann_vol>0 else 0.0
    cum     = (1+r).cumprod()
    mdd     = float(((cum-cum.cummax())/cum.cummax()).min())
    var99   = float(r.quantile(0.01))
    cvar99  = float(r[r<=var99].mean()) if (r<=var99).any() else var99
    var95   = float(r.quantile(0.05))
    cvar95  = float(r[r<=var95].mean()) if (r<=var95).any() else var95
    down_r  = r[r<0]
    sortino = ann_ret/float(down_r.std()*np.sqrt(252)) if len(down_r)>1 else 0.0
    return {
        "ann_vol":ann_vol,"ann_ret":ann_ret,"sharpe":sharpe,
        "max_drawdown":mdd,"var_99_10d":var99*np.sqrt(10),
        "cvar_99_10d":cvar99*np.sqrt(10),"var_95":abs(var95),
        "cvar_95":abs(cvar95),"calmar":ann_ret/abs(mdd) if mdd else 0.0,
        "sortino":sortino,
    }

compute_portfolio_metrics = compute_risk_metrics


def record_trade(portfolio: dict, ticker: str, action: str,
                 qty: float, price: float) -> str:
    total = qty*price
    h     = portfolio.setdefault("holdings",{})
    tr    = portfolio.setdefault("trades",[])
    if action=="BUY":
        if total>portfolio.get("cash",0)+0.01:
            return f"Fonds insuffisants (cash: ${portfolio.get('cash',0):,.0f})"
        portfolio["cash"]-=total
        if ticker in h:
            oq,oa = h[ticker]["qty"],h[ticker]["avg_price"]
            nq = oq+qty
            h[ticker] = {"qty":nq,"avg_price":(oq*oa+qty*price)/nq}
        else:
            h[ticker] = {"qty":qty,"avg_price":price}
    elif action=="SELL":
        avail = h.get(ticker,{}).get("qty",0)
        if avail<qty-1e-9:
            return f"Position insuffisante ({avail:.4f} dispo)"
        portfolio["cash"] = portfolio.get("cash",0)+total
        h[ticker]["qty"] -= qty
        if h[ticker]["qty"]<1e-9: del h[ticker]
    else:
        return f"Action invalide: {action}"
    tr.append({"date":datetime.now().strftime("%Y-%m-%d %H:%M"),
               "ticker":ticker,"action":action,
               "qty":round(qty,6),"price":round(price,6),"total":round(total,2)})
    persist()
    return ""


def get_contract_mult(ticker: str, assets_df=None) -> int:
    if assets_df is not None:
        try:
            row = assets_df[assets_df["ticker"]==ticker]
            if not row.empty and "contract_mult" in row.columns:
                return int(row["contract_mult"].iloc[0])
        except Exception: pass
    return 1 if any(ticker.endswith(s) for s in ["-USD","=X","=F"]) else 100


def get_currency(ticker: str, assets_df=None) -> str:
    if assets_df is not None:
        try:
            row = assets_df[assets_df["ticker"]==ticker]
            if not row.empty and "currency" in row.columns:
                return str(row["currency"].iloc[0])
        except Exception: pass
    if ticker.endswith("=X"):   return "USD"
    if ticker.endswith("-USD"): return "USD"
    if ".PA" in ticker:          return "EUR"
    if ".DE" in ticker or ".AS" in ticker: return "EUR"
    if ".L"  in ticker:          return "GBP"
    return "USD"
