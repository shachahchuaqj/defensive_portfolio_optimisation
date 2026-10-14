# About

Some defensive portfolios are constructed from a basket of SPY, TLT, GLD, FXF, and FXY. Modern Portfolio Theory is used to determine the weights of each component, and a 'lazy' and an 'ideal' portfolio are found from those weights.

The 'lazy' portfolio is subject to the constraint that the return of the portfolio must not be less than $\delta$ from the SPY return, where $\delta$ is kind of like a 'tolerance'. The value of $\delta$ is swept from 0% to 5% in increments of 0.25%, and a new **minimum variance** portfolio is constructed for each $\delta$.

Meanwhile, the 'ideal' portfolio is simply constructed as the max-Sharpe portfolio possible. 

For the Sharpe ratio calculations, the risk-free rate is approximated as the return of BIL as a proxy.

Each portfolio is constructed using rolling 10-year historical data, and their performance is measured started from Jan 2020. The weights are readjusted quarterly after Jan 2020.

A simple 100% SPY portfolio is also used for comparison.

The Sharpe ratio, beta, CVaR, and max drawdown post-Jan 2020 is calculated for each portfolio and reported. CVaR is defined at 95% on daily returns.

Transaction costs are ignored for simplicity. All portfolios are long-only, and fully invested without leverage. 

# Methodology

10-year historical data from Jan 2010 to Jan 2020 is used for the calculation of the first weights for Jan 2020. Subsequent readjustments to the weights every quarter are based on a rolling 10-year window.

Let $P_t$ be the daily closing price. Then the daily return is $r_t = \frac{P_t}{P_{t-1}} - 1$. Simply adding up these returns over $T$ days then dividing by $T$ gives the arithmetic mean of the daily returns; multiplying by 252 gives an estimate for the average annual return. 

The average annual return is calculated for each of the five assets and put into a vector $\boldsymbol{\mu}$. It should be noted that an assumption here is that the daily returns are _indepedent and uncorrelated_ of each other.

$$
\bar{r_i} = \frac{252}{T} \sum_{t=1}^{T}{r_{i,t}}
$$

Meanwhile, the covariance between the i-th and the j-th asset is calculated as $\sigma_{ij} = \frac{1}{T - 1} \sum_{t=1}^{T}{(r_{i,t} - \bar{r_i}) (r_{j,t} - \bar{r_j})}$. As this is a sample covariance, Bessel's correction is used ($T - 1$ instead of $T$), but over a 10-year period, $T$ is so large that even without Bessel's correction, the result should not change that much.

To do this calculation, the daily returns for each asset can be put into an $T \times n$ matrix $R$, where the $(i,j)$-th entry is the return of the $j$-th asset on day $t = i$.

Each column of $R$ is then demeaned to another matrix $X$, meaning that each entry has the column's mean subtracted from it. In other words, $X_{ij} = R_{ij} - \bar{r_j}$. 

Then $\frac{1}{T-1} X^{\text{T}} X = \Sigma$ which is the ($n \times n$) covariance matrix. Each entry in $\Sigma$ is the dot product of one column of $X$ with another column of $X$ (or itself), multiplied by $\frac{1}{T-1}$ which gives the covariance between two assets (or the covariance of an asset with itself, which is just variance).