# Macro Dashboard (FRED + gold/silver)

A self-contained dashboard tracking the 5 biggest drivers of the stock
market, ranked, plus gold and silver spot prices underneath:

1. **Interest rates & Fed policy** — Fed funds rate, 2Y/10Y Treasury yields, the yield curve spread
2. **Inflation** — CPI and core PCE, year-over-year
3. **US dollar & liquidity** — the broad dollar index and M2 money supply
4. **Oil** — WTI crude spot price
5. **Credit spreads & labor market** — high-yield credit spread, nonfarm payrolls, unemployment, jobless claims

(Corporate earnings growth was considered but dropped — the only free
proxy, quarterly corporate profits from FRED, lags too much to be a
useful timely signal alongside the other five, which all update daily
or weekly.)

...plus GDP growth and the VIX in the "everything else" strip, and gold &
silver spot prices in their own section. Macro data comes from the
[FRED API](https://fred.stlouisfed.org/) (Federal Reserve Bank of St. Louis);
gold/silver come from [Stooq](https://stooq.com) (free, no key needed).
Both refresh on a schedule via GitHub Actions — no server, no build step,
just a static page.

`data/metals.json` ships with **sample data** until the workflow runs once
live. Follow the steps below to point everything at live numbers.

## 1. Get a free FRED API key

Sign up (instant, no cost) at
<https://fred.stlouisfed.org/docs/api/api_key.html>. Copy the key — you'll
need it in step 2.

## 2. Add your API key as a repository secret

In this repo on GitHub: **Settings → Secrets and variables → Actions → New
repository secret**.

- Name: `FRED_API_KEY`
- Value: the key from step 1

The scheduled workflow reads this secret; it's never written to a file or
committed.

## 3. Turn on GitHub Pages

**Settings → Pages → Build and deployment → Source: "Deploy from a
branch"** → Branch: `main`, folder: `/ (root)`. Save. GitHub gives you a
URL like `https://<you>.github.io/fred-dashboard/` — that's your live
dashboard.

## 4. Run the update workflow once

**Actions tab → "Update FRED data" → Run workflow.** This pulls real
numbers into `data/latest.json` (FRED) and `data/metals.json` (gold/silver,
no key needed) and commits them, which redeploys the Pages site
automatically. After that it keeps running on its own schedule (weekday
mornings, US time) — see `.github/workflows/update.yml` to change the cron
schedule.

## How it's put together

| File | Purpose |
|---|---|
| `index.html` | The dashboard itself — plain HTML/CSS/JS, no build step, reads `data/latest.json` and `data/metals.json` |
| `scripts/fetch_fred.py` | Pulls the FRED series below, computes YoY/MoM derived values, writes `data/latest.json` |
| `scripts/fetch_metals.py` | Pulls gold & silver spot prices from Stooq (no key needed), writes `data/metals.json` |
| `scripts/generate_sample_data.py` | Produces placeholder sample data for both files (each flagged `"sample": true`) |
| `.github/workflows/update.yml` | Scheduled + manually-triggerable Action that runs both fetch scripts and commits the result |

## Metrics tracked

| Series | FRED ID | Why it's here |
|---|---|---|
| Effective Fed Funds Rate | `DFF` | The policy rate everything else is priced off |
| 2-Year Treasury Yield | `DGS2` | Front-end rate expectations |
| 10-Year Treasury Yield | `DGS10` | Long-end growth/inflation expectations |
| 10Y-2Y Treasury Spread | `T10Y2Y` | Classic recession-warning indicator; negative = inverted |
| CPI, year-over-year | `CPIAUCSL` (derived) | Headline inflation |
| Core PCE, year-over-year | `PCEPILFE` (derived) | The Fed's preferred inflation gauge |
| Unemployment Rate | `UNRATE` | Labor market slack |
| Nonfarm Payrolls, monthly change | `PAYEMS` (derived) | Labor market momentum |
| Initial Jobless Claims | `ICSA` | Highest-frequency labor read (weekly) |
| M2 Money Supply, year-over-year | `M2SL` (derived) | Liquidity backdrop |
| Real GDP Growth, QoQ annualized | `A191RL1Q225SBEA` | Overall growth |
| US Dollar Index (Broad) | `DTWEXBGS` | Cross-asset risk/liquidity proxy |
| CBOE Volatility Index | `VIXCLS` | Equity risk/vol backdrop |
| WTI Crude Oil | `DCOILWTICO` | Inflation input + consumer spending drag |
| High-Yield Credit Spread | `BAMLH0A0HYM2` (ICE BofA US HY OAS) | Risk appetite / credit stress, confirms rate & labor stress |
| Gold Spot | Stooq `XAUUSD` | Not FRED — pulled separately, no key needed |
| Silver Spot | Stooq `XAGUSD` | Not FRED — pulled separately, no key needed |

## Customizing

- **Add/remove a series:** edit the `SERIES` dict at the top of
  `scripts/fetch_fred.py` (any [FRED series ID](https://fred.stlouisfed.org/)
  works), then add a matching card/chart reference in `index.html`.
- **Change the schedule:** edit the `cron` line in
  `.github/workflows/update.yml` ([crontab.guru](https://crontab.guru) helps
  with the syntax). FRED itself only updates as often as each series is
  released — daily series update overnight on business days, monthly
  series (CPI, jobs, PCE) update once a month on their release date.
- **Regenerate sample data:** `python scripts/generate_sample_data.py`.

This dashboard is informational only, not investment advice.

