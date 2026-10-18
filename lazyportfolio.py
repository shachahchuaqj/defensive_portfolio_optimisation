import numpy as np
import pandas as pd
from scipy.optimize import minimize
 
 
class LazyPortfolio:
    def __init__(self, prices: pd.DataFrame, 
                 delta: float, 
                 marketindex: str = "SPY", 
                 window_years: int = 10,
                 start: str = "2020-01-01", 
                 trading_days: int = 252):
        '''
        prices: adjusted daily closes, one column per ticker.
        delta: tolerance for the minimum return of the portfolio relative to the market index 
        (e.g. 0.02 = 2% below market index).
        '''
        self.prices = prices.sort_index()
        self.returns = self.prices.pct_change().dropna() # daily returns
        self.tickers = list(self.prices.columns)
        self.marketindex = marketindex
        self.marketindex_idx = self.tickers.index(marketindex)
        self.delta = delta
        self.window_years = window_years
        self.start = pd.Timestamp(start)
        self.trading_days = trading_days
        self.weights_history = None  # filled by quarterly_weights()

 
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

 
    def weightssolve(self, mu, cov) -> np.ndarray:
        '''
        Solve for the weights of each asset in the portfolio.
        Returns a numpy array of weights.
        '''
        numassets = len(mu)
        floor = mu[self.marketindex_idx] - self.delta
 
        constraints = [
            {"type": "eq",   "fun": lambda w: np.sum(w) - 1.0},   # fully invested
            {"type": "ineq", "fun": lambda w: w @ mu - floor},    # return >= market index return - delta
        ]
        bounds = [(0.0, 1.0)] * numassets                                 # long-only portfolio so weights can only be positive.
 
        w0 = np.zeros(numassets)
        w0[self.marketindex_idx] = 1.0                                    # feasible start: 100% SPY (or whatever else is used)
 
        res = minimize(
            fun=lambda w: w @ cov @ w,      # transpose handled implicitly.
            x0=w0,
            jac=lambda w: 2.0 * cov @ w,
            bounds=bounds,
            constraints=constraints,
            method="SLSQP",
            options={"ftol": 1e-12, "maxiter": 500},
        )
        if not res.success:
            raise RuntimeError(f"SLSQP failed (delta={self.delta}): {res.message}")
 
        w = np.clip(res.x, 0.0, None)
        w /= w.sum()
 
        if w @ mu < floor - 1e-6:
            raise RuntimeError("Return floor violated after clean-up.")
        return w
 

    def weights_at_date(self, date) -> pd.Series:
        '''
        Returns the weights of each asset at a given date.
        '''
        mu, cov = self.metrics(date)
        return pd.Series(self.weightssolve(mu, cov), index=self.tickers, name=pd.Timestamp(date))
 

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
        previous = None
        for date in self.rebalance_dates():
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
        return self.weights_history


from tickerprices import prices

delta = 0.00
deltaweights = dict()
while delta <= 0.05:
    lazy = LazyPortfolio(prices, delta=delta)
    history = lazy.quarterly_weights()
    deltaweights[delta] = history
    delta += 0.0025