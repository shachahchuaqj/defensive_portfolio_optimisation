from __future__ import annotations
 
import numpy as np
import pandas as pd
from scipy.optimize import minimize
 
 
class IdealPortfolio:
    def __init__(self, prices: pd.DataFrame,
                 rf: pd.DataFrame | pd.Series,
                 marketindex: str = "SPY",
                 window_years: int = 10,
                 start: str = "2020-01-01",
                 trading_days: int = 252):
        '''
        prices: adjusted daily closes, one column per ticker.
        rf: annualised 3-month Treasury yields in decimal form (0.0525 = 5.25%), indexed by date.
        '''
        self.prices = prices.sort_index()
        self.returns = self.prices.pct_change().dropna()  # daily returns
        self.tickers = list(self.prices.columns)
        self.marketindex = marketindex
        self.marketindex_idx = self.tickers.index(marketindex)
 
        if isinstance(rf, pd.DataFrame):
            rf = rf.iloc[:, 0]
        self.rf = rf.sort_index()
 
        self.window_years = window_years
        self.start = pd.Timestamp(start)
        self.trading_days = trading_days
        self.weights_history = None  # filled by quarterly_weights()
        self.rf_history = None       # risk-free rate used at each rebalance, filled by quarterly_weights()
 
 
    def metrics(self, currentdate) -> tuple[np.ndarray, np.ndarray]:
        '''
        Gives estimate for annualised mean returns and covariance matrix of returns for the tickers,
        based on a rolling window of historical returns.
        '''
        curdate = pd.Timestamp(currentdate)
        window_start = curdate - pd.DateOffset(years=self.window_years)
 
        if self.returns.index[0] > window_start + pd.Timedelta(days=7):
            raise ValueError(
                f"Not enough history."
            )
 
        mask = (self.returns.index > window_start) & (self.returns.index <= curdate)
        window = self.returns.loc[mask]
 
        mu = window.mean().values * self.trading_days    # annualised arithmetic mean
        cov = window.cov().values * self.trading_days    # annualised covariance
        return mu, cov
 

    def rf_at_date(self, date) -> float:
        '''
        Annualised risk-free rate on the last available day on or before `date` (no look-ahead).
        '''
        value = self.rf.asof(pd.Timestamp(date))
        if pd.isna(value):
            raise ValueError(f"No risk-free rate available on or before {pd.Timestamp(date).date()}.")
        return float(value)


    def weightssolve(self, mu, cov, rf) -> np.ndarray:
        '''
        Solve for the max-Sharpe weights, given annualised mean returns, covariance and risk-free rate.
        Returns a numpy array of weights.
        '''
        numassets = len(mu)
 
        # Positive Sharpe ratio is only possible if at least one asset beats the risk-free rate in long-only portfolio.
        if not np.any(mu - rf > 0):
            raise RuntimeError("No asset has excess return above the risk-free rate; max-Sharpe is undefined.")
 
        def negsharpe(w):
            return -(w @ mu - rf) / np.sqrt(w @ cov @ w)
 
        def negsharpe_grad(w):
            vol = np.sqrt(w @ cov @ w)
            return -(mu / vol - (w @ mu - rf) * (cov @ w) / vol**3)
 
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},   # fully invested
        ]
        bounds = [(0.0, 1.0)] * numassets                       # long-only portfolio so weights can only be positive.
 
        w0 = np.zeros(numassets)
        w0[self.marketindex_idx] = 1.0                          # starting guess: 100% SPY (or whatever else is used)
 
        res = minimize(
            fun=negsharpe,          # maximising Sharpe = minimising negative Sharpe
            x0=w0,
            jac=negsharpe_grad,
            bounds=bounds,
            constraints=constraints,
            method="SLSQP",
            options={"ftol": 1e-9, "maxiter": 500},
        )
        if not res.success:
            raise RuntimeError(f"SLSQP failed (rf={rf:.4f}): {res.message}")
 
        w = np.clip(res.x, 0.0, None)
        w /= w.sum()
 
        if w @ mu - rf <= 0:
            raise RuntimeError("Non-positive excess return after clean-up.")
        return w
 
 
    def weights_at_date(self, date) -> pd.Series:
        '''
        Returns the weights of each asset at a given date.
        '''
        mu, cov = self.metrics(date)
        rf = self.rf_at_date(date)
        return pd.Series(self.weightssolve(mu, cov, rf), index=self.tickers, name=pd.Timestamp(date))
 
 
    def rebalance_dates(self) -> list[pd.Timestamp]:
        '''
        Last trading day before `start`, then every quarter-end trading day after it.
        Weights set on a date use data up to and including that date, and apply from the next trading day.
        Returns list of dates for recalculation of weights.
        '''
        idx = self.returns.index
        first = idx[idx < self.start][-1]
 
        quarter_ends = idx.to_series().groupby(idx.to_period("Q")).last()
        quarter_ends = quarter_ends[(quarter_ends > first) & (quarter_ends < idx[-1])]
        return [first] + list(quarter_ends)
 
 
    def quarterly_weights(self) -> pd.DataFrame:
        '''Returns a DataFrame: one row per rebalance date, one column per ticker.'''
        rows = []
        rf_used = {}
        previous = None
        for date in self.rebalance_dates():
            rf_used[date] = self.rf_at_date(date)
            try:
                w = self.weights_at_date(date)
            except RuntimeError as err:
                if previous is None:
                    raise
                print(f"Warning: {date.date()} solver failed ({err}); keeping previous weights.")
                w = previous.copy()
                w.name = date
            rows.append(w)
            previous = w
 
        self.weights_history = pd.DataFrame(rows)
        self.weights_history.index.name = "rebalance_date"
        self.rf_history = pd.Series(rf_used, name="rf_annual")
        self.rf_history.index.name = "rebalance_date"
        return self.weights_history
 

from tickerprices import prices
from treasuryyields import rf

ideal = IdealPortfolio(prices, rf)
history = ideal.quarterly_weights()
idealport: tuple[IdealPortfolio, pd.DataFrame] = (ideal, history)