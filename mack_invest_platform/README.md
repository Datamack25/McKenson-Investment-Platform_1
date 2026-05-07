# 📈 McKenson Investment Platform - MIP

A full-featured investment simulation platform built with **Streamlit** + **yfinance**.

## Features

### Public Side
- 🎞️ **Live ticker strip** — real-time prices for all assets (SPY, AAPL, MSFT, BTC, indices, FX, commodities…)
- 📰 **Breaking news banner** — scrolling market events
- 💼 **Trading Desk** — spot orders + European options (Black-Scholes)
- 📊 **Technical Analysis** — RSI, MACD, Bollinger Bands, GARCH vol forecast, candlestick charts
- 🧮 **Portfolio Optimizer** — Markowitz + CVaR, efficient frontier, correlation heatmap
- 🏆 **Leaderboard** — team rankings, benchmark comparison (SPY/QQQ/CAC40/Gold/BTC), risk-return map

### Admin Side (password-protected)
- 👥 Manage teams, add/edit/reset
- 📣 Publish live market events
- 💰 Cash injection / penalty
- 🔄 Full game reset
- 📊 Full state view

## Asset Universe
50+ assets including:
- **Equities**: AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, JPM, GS, BNP.PA, AIR.PA…
- **ETFs**: SPY, QQQ
- **Crypto**: BTC-USD, ETH-USD, BNB-USD, SOL-USD, XRP-USD
- **Indices**: ^DJI, ^GSPC, ^NDX, ^FCHI, ^GDAXI, ^FTSE, ^STOXX50E, ^N225, ^HSI, ^VIX
- **Hong Kong**: 0700.HK, 1299.HK, 3690.HK, 9988.HK
- **Japan**: 6758.T, 7203.T, 7974.T, 9432.T, 9984.T
- **Commodities**: GC=F, SI=F, CL=F, BZ=F, MCL=F, CC=F
- **Forex**: EURUSD=X, JPY=X, GBP=X

## Options
European Black-Scholes pricing:
- Contract multiplier = **100** for equities/ETFs, **1** for crypto
- No naked shorts — BUY opens, SELL closes only
- Full greeks: Δ, Γ, θ, ν, ρ

## Quick Start

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/eslsca-stock-game.git
cd eslsca-stock-game

# Install
pip install -r requirements.txt

# Run
streamlit run app.py
```

## Deploy on Streamlit Cloud

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. New app → select repo → `app.py`
4. Deploy 🚀

## Structure

```
eslsca_platform/
├── app.py                  # Entry point
├── requirements.txt
├── data/
│   ├── assets.csv          # All tradeable assets
│   ├── options_positions.csv
│   ├── market_events.csv   # Events / news
│   ├── teams.csv
│   └── game_state.json     # Live game state (auto-created)
├── pages/
│   ├── dashboard.py
│   ├── trading.py
│   ├── technical.py
│   ├── optimizer.py
│   ├── leaderboard.py
│   ├── events.py
│   └── admin.py
├── utils/
│   ├── data.py             # yfinance helpers, state mgmt
│   ├── options.py          # Black-Scholes
│   ├── portfolio.py        # Markowitz, CVaR
│   └── technical.py        # RSI, MACD, Bollinger, GARCH
└── components/
    └── ui.py               # CSS theme, ticker strip, news banner
```

## Admin Password

Default: `MIP2026` — change it in the Admin Panel after first login.

## Teams

Bears 🐻 | Bulls 🐂 | Whales 🐋 | Raptors 🦅 | Sharpas 🦈 | Strikers ⚡ | Wolves 🐺

---
Built for ESLSCA Stock Market Game · 2026
