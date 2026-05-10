# utils/portfolio.py  —  MAM Portfolio Optimization
"""
Markowitz Mean-Variance, CVaR minimization, Efficient Frontier.
MWR (Money-Weighted Return) and TWR (Time-Weighted Return).
"""
from __future__ import annotations
import numpy as np
import pandas as pd

try:
    import cvxpy as cp
    _CVXPY = True
except ImportError:
    _CVXPY = False


# ══════════════════════════════════════════════════════════════════════════════
#  COVARIANCE & RETURNS
# ══════════════════════════════════════════════════════════════════════════════

def compute_stats(prices: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    """Annual returns & covariance from daily price DataFrame."""
    daily = prices.pct_change().dropna()
    mu    = daily.mean() * 252
    cov   = daily.cov() * 252
    return mu, cov


# ══════════════════════════════════════════════════════════════════════════════
#  MARKOWITZ  (Max Sharpe / Min Variance)
# ══════════════════════════════════════════════════════════════════════════════

def markowitz_optimize(mu: pd.Series, cov: pd.DataFrame,
                       rf: float = 0.04,
                       objective: str = "sharpe") -> dict | None:
    """
    Solve Markowitz optimization.
    objective: 'sharpe' | 'min_vol'
    Returns dict with weights, expected return, volatility, sharpe.
    """
    n = len(mu)
    if n < 2:
        return None

    if not _CVXPY:
        # Fallback: equal weight
        w = np.ones(n) / n
        ret = float(mu.values @ w)
        vol = float(np.sqrt(w @ cov.values @ w))
        return {"weights": dict(zip(mu.index, w)),
                "return": ret, "volatility": vol,
                "sharpe": (ret - rf) / vol if vol else 0}

    w   = cp.Variable(n)
    ret = mu.values @ w
    vol = cp.quad_form(w, cov.values)
    constraints = [cp.sum(w) == 1, w >= 0]

    if objective == "sharpe":
        # Maximize Sharpe via parametric approach (maximise return - λ*vol²)
        # We scan multiple risk-aversion levels and pick max Sharpe
        best = None
        for lam in np.logspace(-2, 3, 60):
            prob = cp.Problem(cp.Maximize(ret - lam * vol), constraints)
            try:
                prob.solve(solver=cp.ECOS, warm_start=True)
            except Exception:
                continue
            if w.value is None:
                continue
            wv  = np.clip(w.value, 0, 1)
            wv /= wv.sum() + 1e-12
            r_  = float(mu.values @ wv)
            v_  = float(np.sqrt(wv @ cov.values @ wv))
            sr_ = (r_ - rf) / v_ if v_ > 0 else -999
            if best is None or sr_ > best["sharpe"]:
                best = {"weights": dict(zip(mu.index, wv.tolist())),
                        "return": r_, "volatility": v_, "sharpe": sr_}
        return best

    else:  # min_vol
        prob = cp.Problem(cp.Minimize(vol), constraints)
        try:
            prob.solve(solver=cp.ECOS)
        except Exception:
            return None
        if w.value is None:
            return None
        wv = np.clip(w.value, 0, 1)
        wv /= wv.sum() + 1e-12
        r_ = float(mu.values @ wv)
        v_ = float(np.sqrt(wv @ cov.values @ wv))
        return {"weights": dict(zip(mu.index, wv.tolist())),
                "return": r_, "volatility": v_,
                "sharpe": (r_ - rf) / v_ if v_ > 0 else 0}


# ══════════════════════════════════════════════════════════════════════════════
#  CVaR OPTIMIZATION
# ══════════════════════════════════════════════════════════════════════════════

def cvar_optimize(daily_returns: pd.DataFrame,
                  alpha: float = 0.05,
                  target_return: float | None = None) -> dict | None:
    """Minimize CVaR (Expected Shortfall) at confidence level (1-alpha)."""
    n_assets  = daily_returns.shape[1]
    scenarios = daily_returns.values          # T × N
    T         = scenarios.shape[0]

    if not _CVXPY or T < 30 or n_assets < 2:
        return None

    w  = cp.Variable(n_assets, nonneg=True)
    z  = cp.Variable(T)
    VaR = cp.Variable()

    portfolio_rets = scenarios @ w
    constraints = [
        cp.sum(w) == 1,
        z >= -portfolio_rets - VaR,
        z >= 0,
    ]
    if target_return is not None:
        ann_mu = daily_returns.mean().values * 252
        constraints.append(ann_mu @ w >= target_return)

    cvar = VaR + (1 / (alpha * T)) * cp.sum(z)
    prob = cp.Problem(cp.Minimize(cvar), constraints)
    try:
        prob.solve(solver=cp.ECOS)
    except Exception:
        return None
    if w.value is None:
        return None

    wv = np.clip(w.value, 0, 1)
    wv /= wv.sum() + 1e-12
    ann_ret = float(daily_returns.mean().values * 252 @ wv)
    ann_vol = float(np.sqrt(wv @ (daily_returns.cov().values * 252) @ wv))
    return {"weights": dict(zip(daily_returns.columns, wv.tolist())),
            "return": ann_ret, "volatility": ann_vol,
            "cvar": float(cvar.value) if cvar.value else 0,
            "sharpe": ann_ret / ann_vol if ann_vol > 0 else 0}


# ══════════════════════════════════════════════════════════════════════════════
#  EFFICIENT FRONTIER
# ══════════════════════════════════════════════════════════════════════════════

def efficient_frontier(mu: pd.Series, cov: pd.DataFrame,
                       n_points: int = 60) -> pd.DataFrame:
    """
    Generate efficient frontier points.
    Returns DataFrame with columns: return, volatility, sharpe.
    """
    n = len(mu)
    rows = []

    if not _CVXPY or n < 2:
        # Monte Carlo random portfolios as fallback
        for _ in range(400):
            w = np.random.dirichlet(np.ones(n))
            r = float(mu.values @ w)
            v = float(np.sqrt(w @ cov.values @ w))
            rows.append({"return": r, "volatility": v,
                         "sharpe": r / v if v > 0 else 0})
        return pd.DataFrame(rows)

    w   = cp.Variable(n)
    vol = cp.quad_form(w, cov.values)
    constraints_base = [cp.sum(w) == 1, w >= 0]

    target_rets = np.linspace(float(mu.min()), float(mu.max()), n_points)
    for tr in target_rets:
        constraints = constraints_base + [mu.values @ w >= tr]
        prob = cp.Problem(cp.Minimize(vol), constraints)
        try:
            prob.solve(solver=cp.ECOS, warm_start=True)
        except Exception:
            continue
        if w.value is None:
            continue
        wv  = np.clip(w.value, 0, 1)
        wv /= wv.sum() + 1e-12
        r_  = float(mu.values @ wv)
        v_  = float(np.sqrt(wv @ cov.values @ wv))
        rows.append({"return": r_, "volatility": v_,
                     "sharpe": r_ / v_ if v_ > 0 else 0})

    # Also add random portfolios for interior scatter
    for _ in range(200):
        w2 = np.random.dirichlet(np.ones(n))
        r2 = float(mu.values @ w2)
        v2 = float(np.sqrt(w2 @ cov.values @ w2))
        rows.append({"return": r2, "volatility": v2,
                     "sharpe": r2 / v2 if v2 > 0 else 0})

    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
#  MWR / TWR
# ══════════════════════════════════════════════════════════════════════════════

def compute_twr(sub_period_returns: list[float]) -> float:
    """Time-Weighted Return = product of (1 + ri) - 1."""
    p = 1.0
    for r in sub_period_returns:
        p *= (1 + r)
    return p - 1.0


def compute_mwr(cash_flows: list[tuple[int, float]],
                final_value: float,
                max_iter: int = 500) -> float | None:
    """
    Money-Weighted Return (IRR of cash flows).
    cash_flows: [(day_offset, amount)]  negative = outflow
    final_value: portfolio value at end (positive)
    Returns annualised MWR.
    """
    if not cash_flows:
        return None
    all_cf = list(cash_flows) + [(max(d for d, _ in cash_flows), final_value)]

    r = 0.08 / 365  # initial guess
    for _ in range(max_iter):
        npv  = sum(cf / (1 + r) ** d for d, cf in all_cf)
        dnpv = sum(-d * cf / (1 + r) ** (d + 1) for d, cf in all_cf)
        if abs(dnpv) < 1e-15:
            return None
        r_new = r - npv / dnpv
        if abs(r_new - r) < 1e-12:
            return (1 + r_new) ** 365 - 1
        r = r_new
    return None
