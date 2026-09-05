# Macro Dashboard (FRED)

A self-contained dashboard tracking the macro metrics that matter most for
rates, inflation, labor, and risk — Fed funds rate, the 2Y/10Y yield curve,
CPI, core PCE, unemployment, payrolls, jobless claims, M2, GDP growth, the
dollar index, and the VIX. Data comes straight from the [FRED API](https://fred.stlouisfed.org/)
(Federal Reserve Bank of St. Louis) and refreshes on a schedule via GitHub
Actions — no server, no build step, just a static page.

Right now `data/latest.json` holds **sample data** so the dashboard has
something to show. Follow the steps below to point it at live FRED numbers.

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
numbers into `data/latest.json` and commits them, which redeploys the
Pages site automatically. After that it keeps running on its own schedule
(weekday mornings, US time) — see `.github/workflows/update.yml` to change
the cron schedule.

## How it's put together

| File | Purpose |
|---|---|
| `index.html` | The dashboard itself — plain HTML/CSS/JS, no build step, reads `data/latest.json` |
| `scripts/fetch_fred.py` | Pulls the series list below from FRED, computes YoY/MoM derived values, writes `data/latest.json` |
| `scripts/generate_sample_data.py` | Produces the placeholder sample data (`data/latest.json` with `"sample": true`) |
| `.github/workflows/update.yml` | Scheduled + manually-triggerable Action that runs the fetch script and commits the result |

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

