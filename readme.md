# About

Some defensive portfolios are constructed from a basket of SPY, TLT, GLD, FXF, and FXY. Modern Portfolio Theory is used to determine the weights of each component, and a 'lazy' and an 'ideal' portfolio are found from those weights.

The 'lazy' portfolio is subject to the constraint that the return of the portfolio must not be less than $\delta$ from the SPY return, where $\delta$ is kind of like a 'tolerance'. The value of $\delta$ is swept from 0% to 5% in increments of 0.25%, and a new **minimum variance** portfolio is constructed for each $\delta$.

Meanwhile, the 'ideal' portfolio is simply constructed as the **max-Sharpe** portfolio possible. 

For the Sharpe ratio calculations, the risk-free rate is approximated as the 3-month US Treasury yield.

Each portfolio is constructed using rolling 10-year historical data, and their performance is measured started from Jan 2020. The weights are readjusted quarterly after Jan 2020.

A simple 100% SPY portfolio is also used for comparison.

The Sharpe ratio, beta, CVaR, and max drawdown post-Jan 2020 is calculated for each portfolio and reported. CVaR is defined at 95% on daily returns.

Transaction costs are ignored for simplicity. All portfolios are long-only, and fully invested without leverage. 

# Methodology

10-year historical data from Jan 2010 to Jan 2020 is used for the calculation of the first weights for Jan 2020. Subsequent readjustments to the weights every quarter are based on a rolling 10-year window.

## Portfolio Mathematics

Let $P_t$ be the daily closing price. Then the daily return is $r_t = \frac{P_t}{P_{t-1}} - 1$. Simply adding up these returns over $T$ days then dividing by $T$ gives the arithmetic mean of the daily returns; multiplying by 252 gives an estimate for the average annual return. 

The average annual return is calculated for each of the five assets and put into a vector $\boldsymbol{\mu}$. 

$$
\mu_i = \frac{252}{T} \sum_{t=1}^{T}{r_{i,t}}
$$

If the weights of each asset is put into a vector $\boldsymbol{w}$, then the portfolio return $\mu_p$ is just the dot product of $\boldsymbol{w}$ with $\boldsymbol{\mu}$. 

$$
\mu_p = \boldsymbol{w}^{\text{T}} \boldsymbol{\mu}
$$

Of course, the weights must sum to 1 so $\sum_{i=1}^{5}{w_i} = 1$ which in vector form is $\boldsymbol{1}^{\text{T}} \boldsymbol{w} = 1$. Furthermore, since the portfolios are all long-only, then we also have the constraint that $w_i \geq 0$ for all assets.

Meanwhile, the covariance between the i-th and the j-th asset is calculated as $\sigma_{ij} = \frac{1}{T - 1} \sum_{t=1}^{T}{(r_{i,t} - \overline{r_i}) (r_{j,t} - \overline{r_j})}$. As this is a sample covariance, Bessel's correction is used ($T - 1$ instead of $T$), but over a 10-year period, $T$ is so large that even without Bessel's correction, the result should not change that much.

To do this calculation, the daily returns for each asset can be put into an $T \times 5$ matrix $R$, where the $(i,j)$-th entry is the return of the $j$-th asset on day $t = i$.

Each column of $R$ is then demeaned to another matrix $X$, meaning that each entry has the column's mean subtracted from it. In other words, $X_{ij} = R_{ij} - \overline{r_j}$. 

Then $\frac{252}{T-1} X^{\text{T}} X = \Sigma$ which is the ($5 \times 5$) covariance matrix. Each entry in $\Sigma$ is the dot product of one column of $X$ with another column of $X$ (or itself), multiplied by $\frac{1}{T-1}$ which gives the covariance between two assets (or the covariance of an asset with itself, which is just variance). The factor of 252 is from annualising the covariance matrix (which is for daily data), and because it is assumed that the daily returns are all _mutually independent_.

The portfolio variance is calculated from the entries in the covariance matrix $\Sigma$ and the weights as such:

$$
\sigma_p^2 = \sum_{i} \sum_{j} w_i w_j \Sigma_{ij}
$$

This is just the sum of all entries of $\Sigma$ multiplied by both weights of the assets in question. In matrix form this can be done as such:

$$
\sigma_p^2 = \boldsymbol{w}^{\text{T}} \Sigma \boldsymbol{w}
$$

## Determination of the 'Lazy' Portfolios

For the 'lazy' portfolio with given tolerance $\delta$, the weights are found as the solution to minimising the quantity $\boldsymbol{w}^{\text{T}} \Sigma \boldsymbol{w}$, with the tolerance restriction $\boldsymbol{w}^{\text{T}} \boldsymbol{\mu} \geq \mu_{\text{SPY}} - \delta$.

Since the solution to $\boldsymbol{w}$ could truly be the global minimum variance (if $\mu_p > \mu_{\text{SPY}} - \delta$), or have return equal to the allowed floor ($\mu_p = \mu_{\text{SPY}} - \delta$), SciPy's `minimize` function is used with the SLSQP method. $w_{\text{SPY}} = 1$ and all other weights 0 is used as a starting guess.

## Determination of the 'Ideal' Portfolios

Meanwhile, the 'ideal' portfolio is found by maximising the Sharpe ratio:

$$
S(\boldsymbol{w}) = \frac{\mu_p - r_f}{\sigma_p}
$$

The 3-month US Treasury yield is used as the risk-free rate $r_f$. Technically, the denominator should be the standard deviation of the excess return of the portfolio over the risk-free rate, but $r_f$ is assumed to be a constant and have 0 variance.

Again, SciPy's `minimize` function is used with the SLSQP method to solve for the weights. Once again $w_{\text{SPY}} = 1$ and all other weights 0 is used as a starting guess.