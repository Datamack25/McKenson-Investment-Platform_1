"""
Black-Scholes option pricing utilities.
European options only. Contract multiplier from assets.csv.
"""
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
import pandas as pd
from datetime import date, datetime


def _time_to_expiry(expiry) -> float:
    """Return T in years from today to expiry."""
    if isinstance(expiry, str):
        expiry = datetime.strptime(expiry[:10], "%Y-%m-%d").date()
    today = date.today()
    T = (expiry - today).days / 365.0
    return max(T, 1e-6)


def bs_price(S, K, T, r, sigma, cp: str) -> float:
    """Black-Scholes price. cp = 'C' or 'P'."""
    if T <= 0:
        if cp == "C":
            return max(S - K, 0.0)
        return max(K - S, 0.0)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if cp == "C":
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def bs_delta(S, K, T, r, sigma, cp: str) -> float:
    """Black-Scholes delta."""
    if T <= 0:
        if cp == "C":
            return 1.0 if S > K else 0.0
        return -1.0 if S < K else 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    if cp == "C":
        return norm.cdf(d1)
    return norm.cdf(d1) - 1


def bs_greeks(S, K, T, r, sigma, cp: str) -> dict:
    """Return all main greeks."""
    if T <= 1e-6:
        return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0, "price": bs_price(S, K, T, r, sigma, cp)}
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    delta = norm.cdf(d1) if cp == "C" else norm.cdf(d1) - 1
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    vega = S * norm.pdf(d1) * np.sqrt(T) / 100  # per 1% vol change
    if cp == "C":
        theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
                 - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
        rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
    else:
        theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
                 + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
        rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
    price = bs_price(S, K, T, r, sigma, cp)
    return {"price": price, "delta": delta, "gamma": gamma,
            "theta": theta, "vega": vega, "rho": rho}


def implied_vol(market_price, S, K, T, r, cp: str) -> float:
    """Compute implied volatility via Brent's method."""
    try:
        intrinsic = max(S - K, 0) if cp == "C" else max(K - S, 0)
        if market_price <= intrinsic:
            return np.nan
        f = lambda sigma: bs_price(S, K, T, r, sigma, cp) - market_price
        return brentq(f, 1e-6, 10.0, xtol=1e-6)
    except Exception:
        return np.nan


def price_option_ticket(S, K, expiry, sigma, cp, contract_mult, r=0.045):
    """Full option ticket: price, greeks, cash impact."""
    T = _time_to_expiry(expiry)
    greeks = bs_greeks(S, K, T, r, sigma, cp)
    premium_per_contract = greeks["price"] * contract_mult
    return {
        "T": T,
        "premium": greeks["price"],
        "premium_per_contract": premium_per_contract,
        "delta": greeks["delta"],
        "delta_total": greeks["delta"] * contract_mult,
        "gamma": greeks["gamma"],
        "theta": greeks["theta"],
        "vega": greeks["vega"],
        "rho": greeks["rho"],
    }
