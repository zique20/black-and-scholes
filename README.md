# Black-Scholes Option Pricing — Excel

An Excel implementation of the Black-Scholes model that I built while working through Chapter 6 of Cox & Rubinstein's *Option Markets*. Instead of hard-coding the inputs, the workbook estimates them from raw market data: it pulls volatility out of a price history and the risk-free rate out of a T-Bill quote, then prices European options, computes the Greeks, and cross-checks the result with a Monte Carlo simulation.

## How it works

Black-Scholes needs five inputs: stock price (S), strike (K), time to expiry (t), the risk-free rate (r) and volatility (σ). Three of them you just read off the screen. The other two, r and σ, have to be estimated, and that's really what most of the workbook is doing.

The sheets are wired together, so changing the raw data reprices everything downstream.

### Stock Prices
Takes a column of weekly closing prices and works out the annualized volatility from the log-returns, using the unbiased variance estimator from the book rather than Excel's default `STDEV.P`, which understates it slightly. Basically a rebuild of the book's Table 6-2.

### T-bills
Turns a Treasury bill quote (bid, ask, days to maturity) into the risk-free rate the formula uses.

### BS calc
The actual pricing sheet. You type in S, K and t; r and σ get pulled in from the two sheets above. It returns the call and put price (put via put-call parity) plus the Greeks: delta, gamma, theta, vega, rho.

### Implied vol
Goes the other way. Given a market price, it solves for the volatility the market is pricing in. Black-Scholes can't be inverted on paper, so I do it with Goal Seek: set the model price equal to the market price by changing σ. Comparing this implied vol against the historical one tells you whether options look expensive or cheap relative to what the stock has actually been doing. Cleanest on at-the-money strikes.

### Montecarlo
A second, independent estimate to sanity-check the formula. It simulates thousands of possible prices at expiry under geometric Brownian motion, takes the average payoff and discounts it back. Runs once with historical vol and once with implied vol. I use antithetic variates (drawing Z and -Z) to cut the noise, and the sheet reports a standard error and confidence interval so you can tell a real edge from simulation noise.

## Updating the data

Retyping 27 weeks of prices by hand gets old, so there's a small Python script for it:

```bash
pip3 install yfinance openpyxl
python3 update_bs_model.py
```

It asks for a ticker and the path to the workbook, pulls the last 27 weekly closes from yfinance, drops them into the Stock Prices sheet and updates S on BS calc. Close the file in Excel first, openpyxl can't write to an open workbook. Strike, days to expiry and market price stay manual since they change per option.

## Limitations

- European options only. The right thing to test it on is index options like SPX, which are European by convention, not single-stock US options, which are American.
- Constant volatility. The model assumes one σ for the whole life of the option; real markets have a vol smile/skew, and the Implied vol sheet only shows one point on that curve.
- Lognormal returns, so the tails are thinner than real markets.
- No dividends or borrow cost, which puts a small bias on anything with a meaningful yield.
- Implied vol is least reliable deep in or out of the money, where there's barely any time value to back it out of.
