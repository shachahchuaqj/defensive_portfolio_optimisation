import pandas as pd
import numpy as np
from idealportfolio import IdealPortfolio
from lazyportfolio import LazyPortfolio
from treasuryyields import rf
from tickerprices import prices

class SPYportfolio:
    '''
    100% long-only SPY buy-and-hold portfolio, bought on the last trading day before `start`.
    '''
    def __init__(self, prices: pd.DataFrame,
                 marketindex: str = "SPY",
                 start: str = "2020-01-01"):
        self.prices = prices.sort_index()
        self.returns = self.prices.pct_change().dropna()  # daily returns
        self.tickers = list(self.prices.columns)
        self.marketindex = marketindex
        self.start = pd.Timestamp(start)
 
        idx = self.returns.index
        first = idx[idx < self.start][-1]
 
        w = pd.Series(0.0, index=self.tickers, name=first)
        w[marketindex] = 1.0
        self.weights_history = pd.DataFrame([w])
        self.weights_history.index.name = "rebalance_date"
 
 
    def quarterly_weights(self) -> pd.DataFrame:
        '''Buy-and-hold, hence a single set of weights and never rebalanced.'''
        return self.weights_history

SPY = SPYportfolio(prices)
history = SPY.quarterly_weights()
SPYport = (SPY, history)


class Performance:
    def __init__(self, portfolio: IdealPortfolio | LazyPortfolio | SPYportfolio,
                 rf_history: pd.DataFrame | pd.Series = rf,
                 initial_value: float = 1_000_000,
                 trading_days: int = 252):
        '''
        portfolio: any portfolio object with .returns, .marketindex and .weights_history
                   (each row is target weights per rebalance date).
        rf_history: annualised 3-month Treasury yield as a decimal, indexed by date.
        '''
        self.portfolio = portfolio
        if portfolio.weights_history is None:
            portfolio.quarterly_weights()
        self.weights_history = portfolio.weights_history
 
        if isinstance(rf_history, pd.DataFrame):
            rf_history = rf_history.iloc[:, 0]
        self.rf_history = rf_history.sort_index()
 
        self.initial_value = initial_value
        self.trading_days = trading_days
 
        self.values = None        # portfolio value in dollars, one entry per day (filled by backtest())
        self.port_returns = None  # daily portfolio returns
        self.turnover = None      # sum of |new weight - drifted weight| at each rebalance
        self.backtest()
 
 
    def backtest(self) -> pd.Series:
        '''
        Holds the first set of weights from the day after the first rebalance date, lets the weights
        drift with prices, and resets to the new target weights at the end of each later rebalance date.
        Returns the portfolio value in dollars, starting at `initial_value`.
        '''
        wh = self.weights_history
        rets = self.portfolio.returns[wh.columns]
        first = wh.index[0]
        rets = rets.loc[rets.index > first]
 
        targets = {date: row.values.astype(float) for date, row in wh.iloc[1:].iterrows()}
 
        w = wh.iloc[0].values.astype(float)     # weights vector
        value = float(self.initial_value)
        dates, values, port_rets, turnover = [first], [value], [], {}
 
        for date, r in zip(rets.index, rets.values):        # r is the vector of daily returns
            rp = w @ r                       # return on the weights held from the previous close
            value *= 1.0 + rp
            w = w * (1.0 + r) / (1.0 + rp)   # weights drift with prices
            if date in targets:              # rebalance at the close of this day
                turnover[date] = np.abs(targets[date] - w).sum()
                w = targets[date].copy()
            dates.append(date)
            values.append(value)
            port_rets.append(rp)
 
        self.values = pd.Series(values, index=pd.DatetimeIndex(dates, name="Date"), name="value")
        self.port_returns = pd.Series(port_rets, index=self.values.index[1:], name="return")
        self.turnover = pd.Series(turnover, dtype=float, name="turnover")
        return self.values
 
 
    def daily_rf(self) -> pd.Series:
        '''
        Daily risk-free rate = annualised yield / 252. Each day's return uses the yield from the previous
        trading day (the rate known at the start of that day), so there is no look-ahead.
        '''
        idx = self.values.index
        y = self.rf_history.reindex(self.rf_history.index.union(idx)).ffill().reindex(idx)
        daily = (y.shift(1) / self.trading_days).iloc[1:]
        if daily.isna().any():
            raise ValueError("Risk-free history does not cover the whole backtest period.")
        return daily
 
 
    def final_value(self) -> float:
        '''Portfolio value in dollars at the end of the backtest.'''
        return float(self.values.iloc[-1])
 
 
    def cagr(self) -> float:
        '''Compound annual growth rate over the backtest.'''
        n = len(self.port_returns)
        return float((self.values.iloc[-1] / self.values.iloc[0]) ** (self.trading_days / n) - 1.0)
 
 
    def sharpe_ratio(self) -> float:
        '''
        Annualised Sharpe ratio from the daily excess returns over the risk-free rate:
        sqrt(252) * mean(excess) / std(excess).
        '''
        excess = self.port_returns - self.daily_rf()
        return float(np.sqrt(self.trading_days) * excess.mean() / excess.std(ddof=1))
 
 
    def beta(self) -> float:
        '''Beta of the daily portfolio returns against the market index (SPY): Cov(rp, rm) / Var(rm).'''
        market = self.portfolio.returns[self.portfolio.marketindex].reindex(self.port_returns.index)
        return float(np.cov(self.port_returns.values, market.values, ddof=1)[0, 1] / np.var(market.values, ddof=1))
 
 
    def cvar(self, alpha: float = 0.95) -> float:
        '''
        Historical CVaR on daily returns: the average loss on the worst (1 - alpha) of days.
        Returned as a positive number (0.03 means an average loss of 3% on those days).
        '''
        losses = -self.port_returns.values
        var = np.quantile(losses, alpha)
        return float(losses[losses >= var].mean())
 
 
    def max_drawdown(self) -> float:
        '''
        Largest peak-to-trough fall in portfolio value, as a positive fraction
        (0.30 means the portfolio fell 30% from a previous high).
        '''
        peak = self.values.cummax()
        return float(((peak - self.values) / peak).max())


    def annualised_volatility(self) -> float:
        '''Annualised volatility of daily portfolio returns, using sample standard deviation.'''
        return float(self.port_returns.std(ddof=1) * np.sqrt(self.trading_days))


    def average_weights(self) -> pd.Series:
        '''
        Time-weighted average of the target weights over the test period.
        Weights set at the close of a rebalance date apply from the next trading day, so each
        trading day is matched to the latest rebalance date strictly before it.

        '''
        wh = self.weights_history
        days = self.values.index[1:]
        pos = wh.index.searchsorted(days, side="left") - 1
        return wh.iloc[pos].mean()


    def step_frame(self) -> pd.DataFrame:
        '''
        Express target weights as percentage, extend target weights to last trading day.
        For graph plotting purposes.
        '''
        wh = self.weights_history * 100
        end = self.values.index[-1]
        if wh.index[-1] < end:
            wh = pd.concat([wh, wh.iloc[[-1]].set_axis([end], axis=0)])
        return wh


    
    def summary(self) -> pd.Series:
        '''All headline numbers for this portfolio in one Series.'''
        return pd.Series({
            "Initial value ($)": self.initial_value,
            "Final value ($)": self.final_value(), 
            "Annualised volatility (%)": self.annualised_volatility() * 100,
            "CAGR (%)": self.cagr() * 100,
            "Sharpe ratio": self.sharpe_ratio(),
            "Beta (vs market index)": self.beta(),
            "CVaR 95% daily (%)": self.cvar() * 100,
            "Max drawdown (%)": self.max_drawdown() * 100,
            "Avg turnover per rebalance (%)": float(self.turnover.mean()) * 100 if len(self.turnover) else 0.0,
        })