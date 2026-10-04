# Data Dictionary

## company_master
Reference table built from secondary research. URLs point to company/IR pages intended for verification.

- `ticker`: Yahoo Finance NSE ticker, usually ending in `.NS`.
- `sector`, `industry`: portfolio classification used for comparison.
- `peer_group`: simple analyst-defined peer set.
- `business_summary`: concise business-model context.
- `monitoring_theme`: issues an analyst may monitor; not a recommendation.
- `source_url`: primary company source for context.

## price_daily
Daily OHLCV history pulled with `yfinance` and transformed in Python.

- `return_30d`: percentage price change over 30 trading sessions.
- `volatility_30d`: annualised standard deviation of daily returns using a 30-session rolling window.
- `max_drawdown_90d`: current price relative to the trailing 90-session high.
- `market_score`: transparent rules-based stress score.

## financial_snapshot
Latest available annual financial statement values returned by the public Yahoo Finance interface.

- `revenue`, `net_income`: reported currency units from the source.
- `revenue_growth_pct`, `profit_growth_pct`: year-over-year change versus the prior annual column when available.
- `net_margin_pct`: net income / revenue.
- `debt_equity`: total debt / equity. Not used as a direct comparison metric for banks.
- `roe_pct`: net income / equity.

## news_articles
Recent RSS headlines used as a secondary-attention signal. Headline metadata is not treated as verified fact; users should open the original source.

## etl_run_log
Operational audit trail for scheduled refreshes.
