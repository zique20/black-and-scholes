# Black-Scholes Option Pricing Model — Excel Workbook

An Excel-based implementation of the Black-Scholes option pricing model, built following the methodology in Cox & Rubinstein, *Option Markets* (1985), Chapter 6 — "How to Use the Black-Scholes Formula."

The workbook estimates every input the formula needs from raw, observable market data (historical stock prices, T-Bill quotes), prices European options, computes the Greeks, runs Monte Carlo simulations to cross-check the analytical price, and backs out implied volatility from observed market prices.

---

## Table of Contents

- [Overview](#overview)
- [Sheet-by-sheet breakdown](#sheet-by-sheet-breakdown)
  - [1. Stock Prices](#1-stock-prices--historical-volatility)
  - [2. T-bills](#2-t-bills--risk-free-rate)
  - [3. BS calc](#3-bs-calc--pricing-engine--greeks)
  - [4. Implied vol](#4-implied-vol--inverting-black-scholes)
  - [5. Montecarlo](#5-montecarlo--simulation-cross-check)
- [The five Black-Scholes inputs](#the-five-black-scholes-inputs)
- [Updating data automatically (Python script)](#updating-data-automatically-python-script)
- [Known limitations](#known-limitations)
- [References](#references)

---

## Overview

Black-Scholes prices a European option from five inputs:

| Symbol | Meaning |
|---|---|
| **S** | Current price of the underlying |
| **K** | Strike price |
| **t** | Time to expiration, in years |
| **r** | 1 + risk-free interest rate |
| **σ** | Annualized volatility of the underlying |

Three of these (S, K, t) are directly observable. The other two — r and σ — have to be *estimated* from market data, and that estimation is itself half the model. This workbook builds both estimates from scratch rather than hard-coding them, so the whole pipeline is auditable:

```
Historical prices  →  σ (Stock Prices sheet)
T-Bill quote        →  r (T-bills sheet)
S, K, t (typed in)   →  ┐
σ, r (pulled in)     →  ├─→  BS calc  →  Call/Put price + Greeks
                        ┘
Market price observed →  Implied vol  →  σ implied by the market
σ (either) + S,K,t,r  →  Montecarlo   →  independent price check
```

---

## Sheet-by-sheet breakdown

### 1. Stock Prices — historical volatility

Replicates Cox & Rubinstein's Table 6-2 worksheet for estimating σ from a price history.

**Input:** a column of weekly closing prices for the underlying (`Sj`), oldest at the top, at least ~26 weeks recommended.

**Computed columns:**

| Column | Formula | Meaning |
|---|---|---|
| `Rj = Sj/Sj-1` | price relative | ratio of consecutive prices |
| `log Rj` | `=LN(Rj)` | natural log of the price relative |
| `log Rj - µ̂` | `=log Rj - mean` | deviation from the sample mean |
| `(log Rj - µ̂)²` | squared deviation | for the variance sum |

**Summary statistics block:**

```
n              = count of price relatives
µ̂ (mean)       = (1/n) · Σ log Rj
σ²_ub (unbiased variance) = 1/(n-1) · Σ[(log Rj)² − µ̂²]
annualized variance        = σ²_ub × 52        (weekly data → 52 weeks/year)
annual volatility σ        = √(annualized variance)
```

This is the *unbiased* estimator from the book (correction factor n/(n−1)), not the naive population variance — Excel's default `VAR.P`/`STDEV.P` would understate σ slightly.

> Validated against the book's own worked example (National Semiconductor, Table 6-2): the workbook reproduces σ ≈ 0.52 from the same 27 prices.

---

### 2. T-bills — risk-free rate

Extracts `r` from a quoted T-Bill, exactly as described on p.255 of the book.

**Inputs (from a Treasury quote, e.g. WSJ "Treasury Issues" table):**
- `B` — bid discount
- `A` — asked discount
- `n` — calendar days to maturity (should roughly match the option's expiration)

**Formulas:**

```
T-Bill price = $10,000 × [1 − 0.01 × ((B + A)/2) × (n/360)]
r^-t         = price / 10,000
t            = n / 365
r            = (price/10,000) ^ (-365/n)
```

`r` is "1 plus the interest rate," matching the convention used throughout the model (so `r^(-t)` discounts a future dollar back to today).

> Validated against the book's worked example: B=14.61, A=14.45, n=132 → price=$9,467.23 → r=1.1634, matching the text exactly.

---

### 3. BS calc — pricing engine + Greeks

The core pricing sheet. `S`, `K`, `t` are typed in directly; `r` and `σ` are pulled live from the **T-bills** and **Stock Prices** sheets via cross-sheet references, so changing the historical data automatically reprices the option.

**Black-Scholes formulas:**

```
d1 = [ln(S/K) + (ln(r) + σ²/2)·t] / (σ·√t)
d2 = d1 − σ·√t

Call = S·N(d1) − K·r^(−t)·N(d2)
Put  = Call − S + K·r^(−t)        (put-call parity)
```

`N(·)` is the standard normal CDF, via Excel's `NORM.S.DIST(x,1)`.

**Greeks** (added as a second block on the same sheet):

| Greek | Formula | What it measures |
|---|---|---|
| Delta | `N(d1)` | $ change in option price per $1 move in S |
| Gamma | `φ(d1) / (S·σ·√t)` | rate of change of Delta |
| Theta | (derivative w.r.t. t, /365) | time decay per calendar day |
| Vega | `S·√t·φ(d1) / 100` | $ change per 1 percentage-point change in σ |
| Rho | `K·t·r^(−t)·N(d2)·ln(r) / 100` | $ change per 1 percentage-point change in r |

(`φ(·)` is the standard normal PDF.)

A deep in-the-money call (S far above K) will show Delta ≈ 1, Gamma ≈ 0, and Vega ≈ 0 — the option behaves almost like holding the underlying outright, and its price is barely sensitive to volatility assumptions. An at-the-money option is where the Greeks (and the historical-vs-implied vol comparison) are most informative.

---

### 4. Implied vol — inverting Black-Scholes

Black-Scholes has no closed-form inverse for σ, so this sheet solves for it numerically.

**Inputs:** S, K, t, r (same as BS calc) + the **observed market price** of the option.

**Method used (Goal Seek):**

A helper cell computes the BS call price using a *trial* σ (starting guess, e.g. 0.2):

```
BS Call (trial σ) = S·N(d1) − K·r^(−t)·N(d2)    [same formula, σ = trial value]
```

Then via **Data → What-If Analysis → Goal Seek**:
- *Set cell:* the trial BS price cell
- *To value:* the observed market price
- *By changing cell:* the trial σ cell

Excel iterates the trial σ until the model price matches the market price. The σ that achieves this is the **implied volatility** — what the market, right now, is pricing in for the underlying's future volatility, as opposed to the **historical** σ from the Stock Prices sheet, which only looks backward.

> An attempt was made to automate this with a native Newton-Raphson `LAMBDA`/`LET`/`REDUCE` formula (avoiding manual Goal Seek). This worked in isolated test cases but proved unreliable when composed into the full iterative formula on this particular Excel build, and was reverted in favor of the manual Goal Seek method, which is simple and robust.

**Reading the historical-vs-implied gap:**

| Condition | Interpretation |
|---|---|
| implied ≫ historical | Market pricing more risk than recent history suggests → options relatively expensive |
| implied ≪ historical | Market pricing less risk than recent history suggests → options relatively cheap |
| implied ≈ historical | Fairly priced relative to recent realized volatility |

Caveat: this comparison is cleanest for **at-the-money** options. Deep ITM/OTM options have very little time value, so their implied vol is disproportionately sensitive to small absolute price differences (part of the **volatility smile/skew** phenomenon) — see [Limitations](#known-limitations).

---

### 5. Montecarlo — simulation cross-check

An independent, simulation-based estimate of the option's fair value, used to sanity-check the analytical Black-Scholes price.

**Process:** under the Black-Scholes assumptions, the underlying follows geometric Brownian motion, so its price at expiry can be simulated as:

```
S_T = S × exp[(ln(r) − σ²/2)·t + σ·√t·Z],   Z ~ N(0,1)
```

For each of N draws of Z:
1. Compute `S_T`
2. Compute the payoff `max(S_T − K, 0)`
3. Average all payoffs and discount back: `EV = mean(payoffs) × r^(−t)`

The sheet runs this **twice in parallel** — once using historical σ, once using implied σ — so you can compare the discounted expected value each volatility assumption implies against the actual premium paid.

**Variance reduction — antithetic variates.** A single batch of N random draws is noisy; `EV` swings significantly between recalculations. The sheet mitigates this by drawing N/2 independent `Z` values and mirroring each one as `-Z` for the second half of the simulation. This roughly halves the standard error of `EV` for the same number of draws, without needing to scale N up into territory that makes Excel slow.

The sheet also reports the simulation's standard error and a 95% confidence interval around `EV`, so you can tell whether an apparent "edge" (EV − premium paid) is statistically meaningful or just simulation noise.

---

## The five Black-Scholes inputs

| Input | Where it comes from in this workbook |
|---|---|
| S (stock price) | Typed directly, or pulled from the latest historical price |
| K (strike price) | Typed directly — from the option contract |
| t (time to expiration) | `(days to expiry) / 365` |
| r (1 + interest rate) | Computed from a T-Bill quote, **T-bills** sheet |
| σ (volatility) | Computed from historical log-returns, **Stock Prices** sheet — *or* backed out from a market price, **Implied vol** sheet |

---

## Updating data automatically (Python script)

Manually re-typing 27 weeks of prices every time you want to analyze a new underlying is tedious, so a small Python script automates the **Stock Prices** and **BS calc** S input.

**Requirements:**
```bash
pip3 install yfinance openpyxl
```

**Usage:**
```bash
python3 update_bs_model.py
```

The script will prompt for:
1. A ticker (e.g. `^GSPC` for the S&P 500, `AAPL` for Apple)
2. The path to the workbook (defaults to a hardcoded path if left blank)

It then:
- Pulls the last 27 weekly closes for that ticker via `yfinance`
- Writes them into the **Stock Prices** sheet (column B)
- Updates the current price (S) in **BS calc**
- Saves the workbook

> The Excel file must be **closed** before running the script — `openpyxl` cannot write to a file that Excel has open.

This does *not* automate option-specific inputs (strike, days to expiry, observed market price) — those change per-option and are intentionally left as manual entries on **BS calc** / **Implied vol**.

---

## Known limitations

- **European-style only.** The closed-form Black-Scholes formula prices European options (exercise only at expiry). Most single-stock listed options in the US are American-style; index options (SPX, NDX, XSP) are European by convention and are the correct instruments to test this model against. American options require a different model (e.g. the binomial tree, also covered in Cox & Rubinstein).
- **Constant volatility assumption.** The model assumes σ is fixed over the option's life. Real implied volatility varies by strike (volatility smile/skew) and by time — this workbook's Implied Vol sheet shows you *one point* on that curve, not the curve itself.
- **Lognormal returns.** Monte Carlo and the closed-form price both assume returns are lognormally distributed, which understates the probability of large moves (thin tails) relative to real markets.
- **Implied vol is least informative for deep ITM/OTM options.** Most of the option's value is intrinsic, not time value, so a small absolute pricing difference translates into a large swing in implied σ. Compare historical vs. implied vol on **at-the-money** strikes for a cleaner read.
- **Discrete dividend / borrow cost not modeled.** The formulas as built assume no dividends on the underlying between now and expiry; for indices/stocks with meaningful dividend yield this introduces a small bias.

---

## References

Cox, J. C., & Rubinstein, M. (1985). *Option Markets*. Prentice-Hall, Chapter 6 — "How to Use the Black-Scholes Formula."
