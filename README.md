# 🇮🇳 India Company Intelligence Pro

> **A public live-tracking and research-prioritization platform for Indian listed companies, combining live quotes, technical analytics, fundamentals, multi-source verification and corroborated news.**

[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)
[![Refresh](https://github.com/OWNER/REPO/actions/workflows/refresh_data.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/refresh_data.yml)

## Why this project exists

Analysts often need to combine three separate tasks: collect current market data, understand the latest financial position and do secondary research on the business. Doing that manually across many companies is slow and makes it difficult to maintain a consistent watchlist.

This project turns that workflow into an automated product:

**public data → Python ETL → SQL/SQLite → business metrics → Streamlit dashboard → scheduled GitHub refresh**

The dashboard is designed to answer a practical daily question:

> **What changed across Indian companies, where is attention rising, and what should I investigate next?**

## What the user gets

### 1. Executive Pulse
- Company attention ranking.
- 30-day price momentum.
- 30-day annualised volatility.
- 90-day drawdown.
- Financial pressure indicators.
- 7-day news volume and news-spike flag.
- Risk/momentum maps and downloadable watchlists.

### 2. Company Explorer
Select any company to view:
- price history;
- latest revenue, growth, margin and ROE metrics;
- company business context;
- what to monitor;
- recent research/news headlines;
- link back to the primary company / investor-relations page.

### 3. Sector View
Compare sectors by return, volatility, high-attention company count and recent headline activity.

### 4. Research & News
A structured secondary-research table plus the latest headline metadata discovered through RSS.

### 5. Data & SQL
Shows ETL run history and exposes reusable SQL analysis queries included in the repository.

## Company universe

The seed universe covers 24 large Indian listed businesses across:

- Financials
- Information Technology
- Consumer & FMCG
- Automotive
- Energy & Diversified
- Industrials
- Utilities
- Healthcare
- Materials
- Telecom

The universe is intentionally curated for explainability rather than maximum stock-market coverage. Extend `data/company_master.csv` to add more companies.

## Tech stack

| Layer | Technology |
|---|---|
| Data acquisition | `yfinance`, Google News RSS |
| ETL | Python, pandas, NumPy |
| Storage / SQL | SQLite |
| Visualization | Plotly |
| Web app | Streamlit |
| Automation | GitHub Actions |
| Testing | pytest |
| Deployment | Streamlit Community Cloud or Docker |

## Automated refresh

`.github/workflows/refresh_data.yml` runs on weekdays at **18:00 IST** (12:30 UTC). It:

1. checks out the repository;
2. installs Python dependencies;
3. downloads fresh market and financial data;
4. collects recent headline metadata;
5. calculates derived metrics;
6. validates the database;
7. commits refreshed CSV/SQLite files back to GitHub.

The workflow can also be started manually from the GitHub Actions tab.

## Local setup

```bash
git clone https://github.com/YOUR_USERNAME/india-company-intelligence.git
cd india-company-intelligence
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Run the seed data first if you want to see the dashboard without network access:

```bash
python etl/make_demo_data.py
```

Run a live refresh:

```bash
python etl/run_pipeline.py --period 1y
```

Start the app:

```bash
streamlit run streamlit_app.py
```

Open `http://localhost:8501`.

## GitHub deployment

### Step 1 — Create the repository

Create a **public** repository named something like `india-company-intelligence` and upload the repository contents. The helper script `scripts/publish_to_github.sh` can also push the project from a local terminal.

From the terminal, after creating the empty repository, you can publish with:

```bash
./scripts/publish_to_github.sh https://github.com/YOUR_USERNAME/india-company-intelligence.git
```

### Step 2 — Verify Actions

In **Actions**, allow workflows to run. Trigger **Refresh company intelligence → Run workflow** once manually. The workflow is designed to need **no secrets/API keys**.

### Step 3 — Deploy on Streamlit Community Cloud

Open `https://share.streamlit.io/`, connect GitHub, create a new app and choose:

- Repository: your repository
- Branch: `main`
- Main file: `streamlit_app.py`

Choose a public URL such as `india-company-intelligence.streamlit.app` when available.

### Step 4 — Your live daily workflow

Once deployed:

```text
GitHub Actions (weekday refresh)
             ↓
      CSV + SQLite update
             ↓
     Streamlit redeploys
             ↓
    Public dashboard updates
```

## No API key required

This version deliberately avoids paid API credentials so the project is easy to reproduce publicly. Yahoo Finance data is accessed through `yfinance`. Recent headline discovery uses Google News RSS. Company research links in `company_master.csv` point to company/IR pages for verification.

For professional use, validate important numbers against original NSE filings and issuer materials. NSE provides corporate financial-result and announcement pages that can be used as primary verification sources:

- https://www.nseindia.com/companies-listing/corporate-filings-financial-results
- https://www.nseindia.com/companies-listing/corporate-filings-announcements

## Attention-score logic

The score is **not** an investment rating. It is a research-triage mechanism.

### Market stress
- 30D return below -10% → +2
- 30D return below -5% → +1
- 30D annualised volatility above 40% → +2
- 30D annualised volatility above 25% → +1
- 90D drawdown below -20% → +2
- 90D drawdown below -10% → +1

### Financial pressure
- Negative revenue growth → +1
- Negative profit growth → +1
- Debt/equity above 2x for non-financial sectors → +1

### News attention
- At least 3 headlines in the last 7 days **and** at least 50% more than the previous 7 days → +1

## Responsible-use notes

- This is an analytics and research tool, not investment advice.
- Market data can be delayed or differ from official exchange values.
- Yahoo Finance fields can change and should be cross-checked before professional use.
- News headlines are discovery metadata, not independently verified claims.
- Financial ratios are not directly comparable across every sector, especially banks and other financial institutions.

## Live tracking & verification

The deployed dashboard separates a short-lived live quote layer from the scheduled historical ETL. While a user session is active, Streamlit fragments refresh the live quote and optional watchlist at a user-selected interval. The selected company's quote can be checked against NSE's public quote endpoint; mismatches are explicitly flagged for review. Yahoo Finance's exchange-delay table currently lists NSE data as real-time. For professional tick/order-book applications, use a licensed exchange feed or authenticated broker API.

## Multi-source news intelligence

The news ETL now combines Economic Times, Moneycontrol, Business Standard, LiveMint, Financial Express, BusinessLine and Google News discovery. Headlines are deduplicated, tagged by event type and sentiment, and clustered to show how many distinct sources cover similar stories. The dashboard exposes the source, timestamp, publisher, link, sentiment, event type and corroboration count.

## Important data-use note

The app stores headline metadata and links rather than copying article bodies. Some publishers impose personal/non-commercial or licensing conditions on RSS reuse; commercial redistribution should be reviewed before launch.

## Repository structure

```text
india-company-intelligence/
├── .github/
│   ├── dependabot.yml
│   └── workflows/
│       ├── ci.yml
│       └── refresh_data.yml
├── .streamlit/config.toml
├── app/app.py
├── data/
│   ├── company_master.csv
│   ├── raw/
│   │   ├── financial_snapshot.csv
│   │   ├── news_articles.csv
│   │   └── price_daily.csv
│   └── processed/company_intelligence.db
├── docs/
│   ├── data_dictionary.md
│   └── research_methodology.md
├── etl/
│   ├── make_demo_data.py
│   └── run_pipeline.py
├── sql/
│   ├── analysis_queries.sql
│   └── schema.sql
├── tests/test_pipeline.py
├── Dockerfile
├── Makefile
├── requirements.txt
└── streamlit_app.py
```

## Interview-ready project explanation

**Problem:** Company analysis requires information from disconnected sources and is hard to repeat consistently across a large universe.

**Solution:** I built an automated company-intelligence pipeline covering Indian listed companies. Python handles acquisition/cleaning and derived metrics, SQLite stores the data, SQL supports repeatable screening queries, and Streamlit turns the outputs into an interactive public dashboard. GitHub Actions refreshes the dataset on a schedule so the product remains useful after deployment.

**Business value:** Instead of manually opening multiple sources and comparing companies one by one, an analyst gets a consistent watchlist, sector comparisons and a research queue in one interface.

## Inspired by open-source architecture — not copied

The repository uses common open-source patterns such as Streamlit dashboards, scheduled GitHub Actions and Python market-data retrieval. The problem definition, data model, ETL, attention-score logic and dashboard implementation are original to this project.

## License

MIT — see `LICENSE`.

## v3 dashboard additions

### Analyst Copilot
The `🤖 Analyst Chat` tab provides a deterministic, data-grounded chatbot. It can answer questions about live/latest quote data, attention ranking, 30-day performance, financial metrics, sectors and stored multi-source news. It intentionally does not require an AI API key, which keeps the public Streamlit deployment usable for visitors without exposing credentials.

### Separate stock and volume tracking
The `📊 Stock & Volume` tab separates the market view into two independent interactive charts:
- stock price candlesticks with SMA20, SMA50 and Bollinger Bands;
- a dedicated traded-volume chart with 20-period average volume.

The user can switch among 1d, 5d, 1mo and 3mo periods and intraday/daily intervals supported by the market-data source.

### Graphical technical analysis
The `📐 Technical Graphics` tab adds:
- RSI 14 gauge and trend chart;
- technical signal-balance gauge;
- MACD histogram + signal lines;
- SMA20/SMA50/SMA200;
- ATR14;
- relative volume;
- a numeric technical snapshot.

All technical indicators are descriptive analytics and are not investment advice.
