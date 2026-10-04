# Research & Analytics Methodology

## Problem statement
Indian companies are covered by a fragmented mix of market data, financial statements, corporate pages and news. The project creates a repeatable daily workflow that helps an analyst answer: **What changed, where is the pressure concentrated, and what should I investigate next?**

## Secondary research design
The company universe is intentionally limited to large, recognizable Indian listed businesses so the dashboard remains explainable. Each company has a structured business summary, peer group, monitoring theme and a primary company/IR URL. These fields are analyst research context, not investment ratings.

## Market indicators
The ETL computes 30-day return, 30-day annualised volatility and 90-day drawdown from daily prices. A market stress score is deliberately simple:

- +2 when 30-day return is below -10%; +1 when below -5%.
- +2 when 30-day annualised volatility is above 40%; +1 when above 25%.
- +2 when 90-day drawdown is below -20%; +1 when below -10%.

## Financial indicators
The latest annual statement is compared with the previous annual period when available. Revenue growth, profit growth, net margin and ROE provide business context. Debt/equity is shown for non-financial sectors, but should not be compared directly with banks because their balance sheets are structurally different.

## Attention score
`attention_score = market_score + financial_pressure_score + news_spike_score`

- Financial pressure adds points for negative revenue growth and negative profit growth; non-financial companies can also receive a point for very high debt/equity.
- News spike adds one point when recent 7-day headline volume is both meaningful and materially higher than the preceding 7-day period.

The score is a triage device for research, not an investment recommendation.

## Sources
- NSE India corporate filings and results: https://www.nseindia.com/companies-listing/corporate-filings-financial-results
- NSE India corporate announcements: https://www.nseindia.com/companies-listing/corporate-filings-announcements
- Company investor-relations websites listed in `data/company_master.csv`.
- Market and statement fields accessed via `yfinance`/Yahoo Finance for portfolio analytics.
- Google News RSS is used only for headline discovery and source linking.
