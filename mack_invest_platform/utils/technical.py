"""
Technical analysis: RSI, MACD, Bollinger Bands, simple GARCH volatility forecast.
"""
import numpy as np
import pandas as pd


# ── RSI ───────────────────────────────────────────────────────────────────────

def compute_rsi(prices: pd.Series, period=14) -> pd.Series:
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


# ── MACD ──────────────────────────────────────────────────────────────────────

def compute_macd(prices: pd.Series, fast=12, slow=26, signal=9) -> pd.DataFrame:
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame({
        "MACD": macd_line,
        "Signal": signal_line,
        "Histogram": histogram
    })


# ── Bollinger Bands ────────────────────────────────────────────────────────────

def compute_bollinger(prices: pd.Series, window=20, num_std=2) -> pd.DataFrame:
    sma = prices.rolling(window).mean()
    std = prices.rolling(window).std()
    upper = sma + num_std * std
    lower = sma - num_std * std
    pct_b = (prices - lower) / (upper - lower)
    bandwidth = (upper - lower) / sma
    return pd.DataFrame({
        "SMA": sma,
        "Upper": upper,
        "Lower": lower,
        "%B": pct_b,
        "Bandwidth": bandwidth,
    })


# ── Simple volatility forecast (EWMA/GARCH-like) ─────────────────────────────

def garch_vol_forecast(returns: pd.Series, omega=1e-6, alpha=0.09,
                       beta=0.90, horizon=10) -> list:
    """
    Simple GARCH(1,1)-style multi-step variance forecast.
    Returns list of annualised vol estimates for each step.
    """
    var_long = returns.var()
    # initialise with last EWMA var
    sq = returns**2
    current_var = sq.ewm(span=20).mean().iloc[-1]
    forecasts = []
    for h in range(1, horizon + 1):
        current_var = omega + (alpha + beta) * current_var
        # mean-revert toward long-run variance
        current_var = omega / (1 - alpha - beta) + (alpha + beta)**h * (current_var - omega / (1 - alpha - beta))
        forecasts.append(np.sqrt(current_var * 252))
    return forecasts


# ── Candlestick signal summary ─────────────────────────────────────────────────

def signal_summary(prices: pd.Series) -> dict:
    """Quick signal table from RSI, MACD, Bollinger."""
    rsi = compute_rsi(prices).iloc[-1]
    macd_df = compute_macd(prices)
    boll = compute_bollinger(prices)

    macd_signal = "BUY" if macd_df["MACD"].iloc[-1] > macd_df["Signal"].iloc[-1] else "SELL"
    rsi_signal = "OVERSOLD" if rsi < 30 else ("OVERBOUGHT" if rsi > 70 else "NEUTRAL")
    pct_b = boll["%B"].iloc[-1]
    bb_signal = "OVERSOLD" if pct_b < 0 else ("OVERBOUGHT" if pct_b > 1 else "NEUTRAL")

    return {
        "RSI": round(rsi, 2),
        "RSI_signal": rsi_signal,
        "MACD_signal": macd_signal,
        "MACD_hist": round(macd_df["Histogram"].iloc[-1], 4),
        "BB_%B": round(pct_b, 3),
        "BB_signal": bb_signal,
    }
