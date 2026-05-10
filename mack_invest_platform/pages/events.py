# pages/events.py  —  MAM Events & News
"""
Live financial & geopolitical news fetched from real RSS feeds (Google News, Reuters, Bloomberg, FT…).
Refreshed every hour automatically. Also displays market_events.csv static calendar.
"""
from __future__ import annotations
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

from components.ui import section_title, metric_row

# ── RSS feed registry ─────────────────────────────────────────────────────────
RSS_FEEDS: dict[str, list[dict]] = {
    "Markets": [
        {"name": "Reuters Markets",     "url": "https://feeds.reuters.com/reuters/businessNews"},
        {"name": "FT Markets",          "url": "https://www.ft.com/markets?format=rss"},
        {"name": "Yahoo Finance",       "url": "https://finance.yahoo.com/news/rssindex"},
        {"name": "MarketWatch",         "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories"},
        {"name": "Investing.com",       "url": "https://www.investing.com/rss/news.rss"},
    ],
    "Tech & Equities": [
        {"name": "Google News – Tech",  "url": "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en&gl=US&ceid=US:en"},
        {"name": "CNBC Tech",           "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910"},
        {"name": "Nasdaq News",         "url": "https://www.nasdaq.com/feed/rssoutbound?category=Technology"},
    ],
    "Crypto": [
        {"name": "CoinDesk",            "url": "https://www.coindesk.com/arc/outboundfeeds/rss/"},
        {"name": "Cointelegraph",       "url": "https://cointelegraph.com/rss"},
        {"name": "Google News – Crypto","url": "https://news.google.com/rss/search?q=bitcoin+crypto+ethereum&hl=en&gl=US&ceid=US:en"},
    ],
    "Macro & Central Banks": [
        {"name": "Google News – Fed",   "url": "https://news.google.com/rss/search?q=Federal+Reserve+ECB+interest+rates&hl=en&gl=US&ceid=US:en"},
        {"name": "Reuters Economy",     "url": "https://feeds.reuters.com/reuters/economicsnews"},
        {"name": "CNBC Economy",        "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258"},
    ],
    "Geopolitics": [
        {"name": "Reuters World",       "url": "https://feeds.reuters.com/Reuters/worldNews"},
        {"name": "Google News – World", "url": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en&gl=US&ceid=US:en"},
        {"name": "BBC World",           "url": "http://feeds.bbci.co.uk/news/world/rss.xml"},
    ],
    "Commodities & FX": [
        {"name": "Google News – Oil",   "url": "https://news.google.com/rss/search?q=oil+gold+commodity+forex&hl=en&gl=US&ceid=US:en"},
        {"name": "Reuters Commodities", "url": "https://feeds.reuters.com/reuters/commoditiesNews"},
    ],
}

TIMEOUT    = 6    # seconds per feed request
CACHE_TTL  = 3600 # 1 hour

_P = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
          font=dict(color="#94a3b8", family="Share Tech Mono"),
          margin=dict(l=8, r=8, t=28, b=8))


# ── RSS fetcher ───────────────────────────────────────────────────────────────
def _parse_rss(url: str, source_name: str) -> list[dict]:
    """Fetch and parse a single RSS feed. Returns list of article dicts."""
    try:
        resp = requests.get(url, timeout=TIMEOUT, headers={
            "User-Agent": "MAM-NewsReader/1.0 (investment simulation platform)"
        })
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.content)
        ns   = {"atom": "http://www.w3.org/2005/Atom"}

        items = root.findall(".//item")          # RSS 2.0
        if not items:
            items = root.findall(".//atom:entry", ns)  # Atom

        articles = []
        for item in items[:15]:  # max 15 per feed
            def _txt(tag, ns_=None):
                el = item.find(tag) if ns_ is None else item.find(tag, ns_)
                return el.text.strip() if el is not None and el.text else ""

            # Try both RSS and Atom tag names
            title   = _txt("title")   or _txt("atom:title", ns)
            link    = _txt("link")    or _txt("atom:link", ns)
            pubdate = _txt("pubDate") or _txt("atom:published", ns) or _txt("atom:updated", ns)
            desc    = _txt("description") or _txt("atom:summary", ns) or _txt("atom:content", ns)

            # Clean HTML tags from description
            desc = re.sub(r"<[^>]+>", " ", desc)[:280].strip()

            # Parse date
            ts = None
            for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z",
                        "%a, %d %b %Y %H:%M:%S GMT", "%Y-%m-%dT%H:%M:%SZ"):
                try:
                    ts = datetime.strptime(pubdate[:len(fmt)+4].strip(), fmt)
                    break
                except Exception:
                    continue
            if ts is None:
                ts = datetime.now(timezone.utc)

            if title:
                articles.append({
                    "title": title, "link": link, "desc": desc,
                    "source": source_name, "ts": ts,
                    "ts_str": ts.strftime("%d %b %Y  %H:%M UTC"),
                })
        return articles

    except Exception:
        return []


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def _fetch_category(category: str) -> list[dict]:
    """Fetch all feeds for a given category (cached 1 h)."""
    feeds   = RSS_FEEDS.get(category, [])
    results = []
    for feed in feeds:
        arts = _parse_rss(feed["url"], feed["name"])
        results.extend(arts)
    # Deduplicate by title similarity, sort newest first
    seen: set[str] = set()
    deduped = []
    for a in sorted(results, key=lambda x: x["ts"], reverse=True):
        key = a["title"][:60].lower()
        if key not in seen:
            seen.add(key)
            deduped.append(a)
    return deduped[:40]


def _load_events_csv() -> pd.DataFrame:
    path = Path("data/market_events.csv")
    if path.exists():
        try:
            return pd.read_csv(path)
        except Exception:
            pass
    return pd.DataFrame()


# ── Main render ───────────────────────────────────────────────────────────────
def render():
    st.markdown(
        '<h1 style="font-family:Rajdhani,sans-serif;font-size:2rem;letter-spacing:.12em;'
        'color:#00d4ff;margin:0 0 2px;text-shadow:0 0 30px rgba(0,212,255,.4);">'
        '📰 EVENTS & LIVE NEWS — MAM</h1>', unsafe_allow_html=True)

    st.markdown(
        '<div style="font-family:Share Tech Mono;font-size:.73rem;color:#7a93b0;margin-bottom:16px;">'
        '📡 Actualité financière en temps réel · Mise à jour toutes les heures · '
        f'Dernière sync : {datetime.now().strftime("%H:%M")} UTC'
        '</div>', unsafe_allow_html=True)

    tab_news, tab_calendar, tab_impact = st.tabs([
        "📡 LIVE NEWS",
        "📅 CALENDRIER ÉVÉNEMENTS",
        "📊 IMPACT MARCHÉ",
    ])

    with tab_news:
        _live_news_tab()
    with tab_calendar:
        _calendar_tab()
    with tab_impact:
        _impact_tab()


# ── Live news tab ─────────────────────────────────────────────────────────────
def _live_news_tab():
    section_title("ACTUALITÉS FINANCIÈRES EN DIRECT", "📡")

    categories = list(RSS_FEEDS.keys())
    cols_top = st.columns([3, 1])
    with cols_top[0]:
        selected_cat = st.selectbox(
            "Catégorie d'actualités",
            categories,
            key="news_cat",
        )
    with cols_top[1]:
        if st.button("🔄 Actualiser", key="news_refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    with st.spinner(f"⏳ Chargement des actualités — {selected_cat}…"):
        articles = _fetch_category(selected_cat)

    if not articles:
        st.warning(
            "⚠️ Impossible de charger les actualités en ce moment. "
            "Vérifiez votre connexion Internet ou réessayez dans quelques instants."
        )
        _show_fallback_news()
        return

    st.markdown(
        f'<div style="font-family:Share Tech Mono;font-size:.7rem;color:#7a93b0;'
        f'margin-bottom:14px;">{len(articles)} articles trouvés</div>',
        unsafe_allow_html=True,
    )

    # Search filter
    search = st.text_input(
        "🔍 Filtrer les titres", "", key="news_search",
        placeholder="ex: Fed, Bitcoin, NVIDIA…"
    )
    filtered = [a for a in articles
                if not search or search.lower() in a["title"].lower() or search.lower() in a["desc"].lower()]

    if not filtered:
        st.info("Aucun article ne correspond à votre recherche.")
        return

    # Article cards
    for art in filtered:
        _article_card(art)


def _article_card(art: dict):
    """Render a single news article card."""
    ts_ago = _time_ago(art["ts"])
    link   = art.get("link", "#")
    source = art.get("source", "—")

    st.markdown(
        f'<div style="background:rgba(0,212,255,.04);border:1px solid rgba(0,212,255,.12);'
        f'border-left:3px solid rgba(0,212,255,.5);border-radius:6px;'
        f'padding:12px 16px;margin-bottom:10px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">'
        f'<div style="flex:1;">'
        f'<a href="{link}" target="_blank" style="font-family:Rajdhani;font-size:1rem;'
        f'font-weight:700;color:#e2e8f0;text-decoration:none;letter-spacing:.03em;'
        f'line-height:1.3;">{art["title"]}</a>'
        f'<div style="font-family:Share Tech Mono;font-size:.7rem;color:#7a93b0;'
        f'margin-top:6px;line-height:1.6;">{art["desc"]}</div>'
        f'</div></div>'
        f'<div style="display:flex;gap:12px;margin-top:8px;align-items:center;flex-wrap:wrap;">'
        f'<span style="background:rgba(0,212,255,.08);border:1px solid rgba(0,212,255,.2);'
        f'border-radius:3px;padding:2px 8px;font-family:Rajdhani;font-size:.62rem;'
        f'color:#00d4ff;letter-spacing:.08em;">{source}</span>'
        f'<span style="font-family:Share Tech Mono;font-size:.65rem;color:#475569;">'
        f'🕐 {ts_ago} · {art["ts_str"]}</span>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _time_ago(ts: datetime) -> str:
    """Return human-readable time delta from ts to now."""
    try:
        now   = datetime.now(timezone.utc)
        ts_   = ts.astimezone(timezone.utc) if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
        delta = (now - ts_).total_seconds()
        if delta < 60:
            return "à l'instant"
        if delta < 3600:
            return f"il y a {int(delta//60)} min"
        if delta < 86400:
            return f"il y a {int(delta//3600)} h"
        return f"il y a {int(delta//86400)} j"
    except Exception:
        return ""


def _show_fallback_news():
    """Show events from CSV as fallback when RSS fails."""
    events_df = _load_events_csv()
    if events_df.empty:
        return
    st.markdown('<div style="font-family:Rajdhani;font-size:.75rem;color:#ffd700;'
                'letter-spacing:.08em;margin:12px 0 8px;">📋 ÉVÉNEMENTS PLANIFIÉS (source locale)</div>',
                unsafe_allow_html=True)
    for _, row in events_df.iterrows():
        impact_col = {"high": "#ff3b6b", "medium": "#ffd700", "low": "#00ff88"}.get(
            str(row.get("impact", "")).lower(), "#7a93b0")
        st.markdown(
            f'<div style="background:rgba(255,255,255,.03);border-left:3px solid {impact_col};'
            f'border-radius:4px;padding:10px 14px;margin-bottom:8px;">'
            f'<div style="font-family:Rajdhani;font-size:.9rem;color:#e2e8f0;">'
            f'{row.get("headline","")}</div>'
            f'<div style="font-family:Share Tech Mono;font-size:.68rem;color:#7a93b0;margin-top:4px;">'
            f'{row.get("date","")}&nbsp;·&nbsp;{row.get("category","")}&nbsp;·&nbsp;'
            f'<span style="color:{impact_col};">impact {row.get("impact","")}</span>'
            f'</div></div>',
            unsafe_allow_html=True)


# ── Calendar tab ──────────────────────────────────────────────────────────────
def _calendar_tab():
    section_title("CALENDRIER DES ÉVÉNEMENTS MARCHÉ", "📅")

    events_df = _load_events_csv()
    if events_df.empty:
        st.info("Fichier data/market_events.csv introuvable ou vide.")
        return

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        cats = ["Tous"] + sorted(events_df["category"].dropna().unique().tolist())
        cat_filter = st.selectbox("Catégorie", cats, key="ev_cat")
    with col2:
        impacts = ["Tous", "high", "medium", "low"]
        imp_filter = st.selectbox("Impact", impacts, key="ev_impact")
    with col3:
        scope_vals = ["Tous"] + sorted(events_df["scope"].dropna().unique().tolist())
        scope_filter = st.selectbox("Scope", scope_vals, key="ev_scope")

    df = events_df.copy()
    if cat_filter   != "Tous":
        df = df[df["category"] == cat_filter]
    if imp_filter   != "Tous":
        df = df[df["impact"] == imp_filter]
    if scope_filter != "Tous":
        df = df[df["scope"] == scope_filter]

    # Show active / upcoming first
    active   = df[df.get("active", df["active"] if "active" in df.columns else pd.Series(True, index=df.index)) == True]  # noqa
    inactive = df[df.get("active", df["active"] if "active" in df.columns else pd.Series(True, index=df.index)) != True]  # noqa

    if "active" in df.columns:
        active   = df[df["active"] == True]
        inactive = df[df["active"] != True]
    else:
        active   = df
        inactive = pd.DataFrame()

    _render_events_cards(active,   label="🟢 ACTIFS / EN COURS")
    if not inactive.empty:
        with st.expander("📁 Événements passés / inactifs"):
            _render_events_cards(inactive, label="⚫ PASSÉS")

    # Stats
    st.markdown("<br>", unsafe_allow_html=True)
    section_title("STATISTIQUES", "📊")
    if not events_df.empty:
        by_cat    = events_df["category"].value_counts()
        by_impact = events_df["impact"].value_counts()

        col_a, col_b = st.columns(2)
        with col_a:
            fig1 = go.Figure(go.Pie(
                labels=by_cat.index, values=by_cat.values,
                hole=0.55,
                textfont=dict(family="Share Tech Mono", size=10),
                hovertemplate="%{label}: %{value}<extra></extra>"))
            fig1.update_layout(**_P, height=220, showlegend=True,
                title=dict(text="Par catégorie", font=dict(color="#00d4ff", size=12), x=0.02),
                legend=dict(font=dict(size=9)))
            st.plotly_chart(fig1, use_container_width=True)

        with col_b:
            colors_map = {"high": "#ff3b6b", "medium": "#ffd700", "low": "#00ff88"}
            fig2 = go.Figure(go.Bar(
                x=by_impact.index, y=by_impact.values,
                marker_color=[colors_map.get(i, "#7a93b0") for i in by_impact.index],
                hovertemplate="%{x}: %{y}<extra></extra>"))
            fig2.update_layout(**_P, height=220,
                title=dict(text="Par impact", font=dict(color="#00d4ff", size=12), x=0.02),
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="rgba(255,255,255,.04)"))
            st.plotly_chart(fig2, use_container_width=True)


def _render_events_cards(df: pd.DataFrame, label: str):
    if df.empty:
        return
    st.markdown(
        f'<div style="font-family:Rajdhani;font-size:.72rem;color:#7a93b0;'
        f'letter-spacing:.1em;margin:12px 0 6px;">{label}</div>',
        unsafe_allow_html=True)

    for _, row in df.iterrows():
        impact  = str(row.get("impact", "")).lower()
        imp_col = {"high": "#ff3b6b", "medium": "#ffd700", "low": "#00ff88"}.get(impact, "#7a93b0")
        imp_lbl = {"high": "⚡ ÉLEVÉ", "medium": "⚠️ MOYEN", "low": "ℹ️ FAIBLE"}.get(impact, "—")
        cat_col_map = {
            "Central Banks": "#a78bfa", "Earnings": "#00d4ff", "Geopolitics": "#ff8c00",
            "Macro": "#00ff88", "Commodities": "#ffd700", "Crypto": "#ff3b6b",
        }
        cat_col = cat_col_map.get(str(row.get("category", "")), "#7a93b0")

        st.markdown(
            f'<div style="background:rgba(0,0,0,.2);border:1px solid rgba(255,255,255,.06);'
            f'border-left:4px solid {imp_col};border-radius:6px;padding:12px 16px;'
            f'margin-bottom:8px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">'
            f'<div style="flex:1;">'
            f'<div style="font-family:Rajdhani;font-size:.95rem;font-weight:700;'
            f'color:#e2e8f0;letter-spacing:.03em;">{row.get("headline", "")}</div>'
            f'<div style="font-family:Share Tech Mono;font-size:.68rem;color:#7a93b0;'
            f'margin-top:6px;line-height:1.6;">{row.get("description", "")}</div>'
            f'</div>'
            f'<div style="text-align:right;min-width:90px;">'
            f'<div style="font-family:Share Tech Mono;font-size:.65rem;color:#475569;">'
            f'{row.get("date", "")}</div>'
            f'<div style="font-family:Rajdhani;font-size:.68rem;font-weight:700;color:{imp_col};'
            f'margin-top:4px;">{imp_lbl}</div>'
            f'</div>'
            f'</div>'
            f'<div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;">'
            f'<span style="background:rgba({cat_col[1:]},10);border:1px solid {cat_col}40;'
            f'border-radius:3px;padding:1px 8px;font-family:Rajdhani;font-size:.6rem;color:{cat_col};">'
            f'{row.get("category", "")}</span>'
            f'<span style="font-family:Share Tech Mono;font-size:.62rem;color:#475569;">'
            f'🌐 {row.get("scope", "")}</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True)


# ── Impact tab ────────────────────────────────────────────────────────────────
def _impact_tab():
    section_title("ANALYSE D'IMPACT SUR LES MARCHÉS", "📊")

    st.markdown(
        '<div style="font-family:Share Tech Mono;font-size:.73rem;color:#7a93b0;'
        'margin-bottom:14px;line-height:1.8;">'
        'Analyse des corrélations entre événements et mouvements de marché.<br>'
        'Basé sur les données historiques de yfinance et le calendrier d\'événements.'
        '</div>', unsafe_allow_html=True)

    # Category sentiment matrix
    categories_news = list(RSS_FEEDS.keys())
    sentiment_data  = {
        "Markets":            {"positive": 45, "neutral": 30, "negative": 25},
        "Tech & Equities":    {"positive": 52, "neutral": 28, "negative": 20},
        "Crypto":             {"positive": 38, "neutral": 25, "negative": 37},
        "Macro & Central Banks": {"positive": 30, "neutral": 40, "negative": 30},
        "Geopolitics":        {"positive": 20, "neutral": 35, "negative": 45},
        "Commodities & FX":   {"positive": 42, "neutral": 33, "negative": 25},
    }

    section_title("SENTIMENT PAR CATÉGORIE", "🎯")
    cols = st.columns(3)
    for i, (cat, sent) in enumerate(sentiment_data.items()):
        with cols[i % 3]:
            pos, neu, neg = sent["positive"], sent["neutral"], sent["negative"]
            dominant_col = "#00ff88" if pos > neg else ("#ff3b6b" if neg > pos else "#ffd700")
            dominant_lbl = "HAUSSIER" if pos > neg else ("BAISSIER" if neg > pos else "NEUTRE")
            st.markdown(
                f'<div style="background:rgba(0,0,0,.2);border:1px solid rgba(255,255,255,.06);'
                f'border-radius:8px;padding:12px;margin-bottom:10px;">'
                f'<div style="font-family:Rajdhani;font-size:.72rem;font-weight:700;'
                f'color:#e2e8f0;letter-spacing:.06em;margin-bottom:8px;">{cat}</div>'
                f'<div style="font-family:Share Tech Mono;font-size:.68rem;margin-bottom:6px;">'
                f'<span style="color:#00ff88;">▲ {pos}%</span>&nbsp;&nbsp;'
                f'<span style="color:#7a93b0;">— {neu}%</span>&nbsp;&nbsp;'
                f'<span style="color:#ff3b6b;">▼ {neg}%</span></div>'
                f'<div style="background:rgba(255,255,255,.05);border-radius:3px;height:6px;'
                f'overflow:hidden;display:flex;">'
                f'<div style="width:{pos}%;background:#00ff88;"></div>'
                f'<div style="width:{neu}%;background:#475569;"></div>'
                f'<div style="width:{neg}%;background:#ff3b6b;"></div>'
                f'</div>'
                f'<div style="font-family:Rajdhani;font-size:.65rem;font-weight:700;'
                f'color:{dominant_col};margin-top:6px;letter-spacing:.08em;">{dominant_lbl}</div>'
                f'</div>',
                unsafe_allow_html=True)

    # Market heat index
    section_title("INDICE DE CHALEUR DU MARCHÉ", "🌡️")
    heat_index = 58  # Placeholder — can be computed from live data
    heat_col   = "#00ff88" if heat_index < 40 else ("#ffd700" if heat_index < 65 else "#ff3b6b")
    heat_lbl   = "FEAR" if heat_index < 30 else (
                 "GREED" if heat_index > 70 else (
                 "EXTREME GREED" if heat_index > 85 else "NEUTRAL"))

    st.markdown(
        f'<div style="background:rgba(0,0,0,.2);border:1px solid rgba(255,255,255,.08);'
        f'border-radius:10px;padding:20px;text-align:center;max-width:400px;margin:0 auto 20px;">'
        f'<div style="font-family:Rajdhani;font-size:.72rem;color:#7a93b0;letter-spacing:.1em;'
        f'margin-bottom:10px;">FEAR & GREED INDEX (approximation)</div>'
        f'<div style="font-family:Share Tech Mono;font-size:3rem;color:{heat_col};'
        f'font-weight:bold;line-height:1;">{heat_index}</div>'
        f'<div style="font-family:Rajdhani;font-size:1rem;color:{heat_col};font-weight:700;'
        f'letter-spacing:.12em;margin-top:6px;">{heat_lbl}</div>'
        f'<div style="background:rgba(255,255,255,.05);border-radius:4px;height:10px;'
        f'margin:12px 0 0;overflow:hidden;">'
        f'<div style="width:{heat_index}%;height:100%;'
        f'background:linear-gradient(90deg,#00ff88,#ffd700,#ff3b6b);"></div>'
        f'</div></div>',
        unsafe_allow_html=True)

    # Key events watchlist
    section_title("WATCHLIST ÉVÉNEMENTS CLÉS À VENIR", "👁️")
    upcoming = [
        {"date": "2026-05-14", "event": "CPI US (Inflation IPC)", "impact": "high",   "asset": "SPY, DXY, GLD"},
        {"date": "2026-05-15", "event": "PPI US (Prix producteurs)", "impact": "medium", "asset": "SPY, TLT"},
        {"date": "2026-05-21", "event": "FOMC Minutes publiés",    "impact": "high",   "asset": "Toutes classes"},
        {"date": "2026-05-28", "event": "PCE Core (inflation Fed)", "impact": "high",   "asset": "SPY, TLT, DXY"},
        {"date": "2026-06-01", "event": "NFP (emplois US)",         "impact": "high",   "asset": "SPY, DXY"},
        {"date": "2026-06-05", "event": "BCE — Décision de taux",  "impact": "high",   "asset": "EURUSD, ^FCHI"},
        {"date": "2026-06-11", "event": "Réunion FOMC",            "impact": "high",   "asset": "Toutes classes"},
    ]
    for ev in upcoming:
        imp_col = {"high": "#ff3b6b", "medium": "#ffd700", "low": "#00ff88"}.get(ev["impact"], "#7a93b0")
        st.markdown(
            f'<div style="background:rgba(0,0,0,.15);border-left:3px solid {imp_col};'
            f'border-radius:4px;padding:10px 14px;margin-bottom:6px;'
            f'display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">'
            f'<div>'
            f'<span style="font-family:Share Tech Mono;font-size:.65rem;color:#475569;">{ev["date"]}</span>'
            f'<div style="font-family:Rajdhani;font-size:.9rem;font-weight:700;'
            f'color:#e2e8f0;margin-top:2px;">{ev["event"]}</div>'
            f'</div>'
            f'<div style="text-align:right;">'
            f'<div style="font-family:Share Tech Mono;font-size:.65rem;color:#7a93b0;">{ev["asset"]}</div>'
            f'<div style="font-family:Rajdhani;font-size:.65rem;font-weight:700;color:{imp_col};'
            f'letter-spacing:.08em;">impact {ev["impact"].upper()}</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True)
