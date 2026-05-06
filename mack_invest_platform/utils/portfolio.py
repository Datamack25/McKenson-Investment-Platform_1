"""
Portfolio analytics: Markowitz optimisation, CVaR, Sharpe, drawdown, VaR.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize


# ── Risk metrics ──────────────────────────────────────────────────────────────

def portfolio_returns(weights: np.ndarray, ret_matrix: pd.DataFrame) -> np.ndarray:
    return ret_matrix.values @ weights


def sharpe_ratio(weights, ret_matrix, rf=0.045/252) -> float:
    rets = portfolio_returns(weights, ret_matrix)
    excess = rets - rf
    if excess.std() == 0:
        return 0.0
    return (excess.mean() / excess.std()) * np.sqrt(252)


def annualised_vol(weights, ret_matrix) -> float:
    rets = portfolio_returns(weights, ret_matrix)
    return rets.std() * np.sqrt(252)


def max_drawdown(portfolio_values: pd.Series) -> float:
    roll_max = portfolio_values.cummax()
    drawdown = (portfolio_values - roll_max) / roll_max
    return drawdown.min()


def var_parametric(weights, ret_matrix, confidence=0.99, horizon=10) -> float:
    """Parametric VaR at given confidence for horizon days."""
    rets = portfolio_returns(weights, ret_matrix)
    mu = rets.mean()
    sigma = rets.std()
    z = {0.95: 1.645, 0.99: 2.326, 0.999: 3.090}.get(confidence, 2.326)
    return (-mu * horizon + z * sigma * np.sqrt(horizon))


def cvar_historical(weights, ret_matrix, confidence=0.99) -> float:
    """Historical CVaR (Expected Shortfall)."""
    rets = portfolio_returns(weights, ret_matrix)
    cutoff = np.percentile(rets, (1 - confidence) * 100)
    tail = rets[rets <= cutoff]
    return -tail.mean() if len(tail) > 0 else 0.0


# ── Markowitz + CVaR optimisation ─────────────────────────────────────────────

def markowitz_optimise(ret_matrix: pd.DataFrame, target_return=None,
                       allow_short=False, cvar_weight=0.0,
                       confidence=0.95) -> dict:
    """
    Minimise portfolio variance (+ optional CVaR penalty).
    Returns dict with weights, metrics.
    """
    n = ret_matrix.shape[1]
    tickers = ret_matrix.columns.tolist()
    mean_rets = ret_matrix.mean().values
    cov = ret_matrix.cov().values

    bounds = ((-1, 1) if allow_short else (0, 1),) * n
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    if target_return is not None:
        constraints.append({
            "type": "eq",
            "fun": lambda w: w @ mean_rets - target_return
        })

    def objective(w):
        var = w @ cov @ w
        cvar_pen = 0.0
        if cvar_weight > 0:
            cvar_pen = cvar_historical(w, ret_matrix, confidence) * cvar_weight
        return var + cvar_pen

    w0 = np.ones(n) / n
    res = minimize(objective, w0, method="SLSQP",
                   bounds=bounds, constraints=constraints,
                   options={"maxiter": 1000, "ftol": 1e-9})

    w = res.x if res.success else w0
    rets = portfolio_returns(w, ret_matrix)
    return {
        "weights": dict(zip(tickers, w)),
        "expected_return": float(w @ mean_rets * 252),
        "volatility": float(annualised_vol(w, ret_matrix)),
        "sharpe": float(sharpe_ratio(w, ret_matrix)),
        "cvar_95": float(cvar_historical(w, ret_matrix, 0.95)),
        "cvar_99": float(cvar_historical(w, ret_matrix, 0.99)),
        "success": res.success,
    }


def efficient_frontier(ret_matrix: pd.DataFrame, n_points=50) -> pd.DataFrame:
    """Compute efficient frontier points."""
    mean_rets = ret_matrix.mean().values * 252
    min_r = mean_rets.min()
    max_r = mean_rets.max()
    targets = np.linspace(min_r * 0.8, max_r * 0.95, n_points)
    records = []
    for t in targets:
        try:
            res = markowitz_optimise(ret_matrix, target_return=t / 252)
            records.append({"return": res["expected_return"],
                            "vol": res["volatility"],
                            "sharpe": res["sharpe"]})
        except Exception:
            pass
    return pd.DataFrame(records)
