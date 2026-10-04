# Live architecture

The project now has two deliberate data paths.

## 1. Live market layer

The Streamlit app fetches the selected company's latest quote and a small live watchlist while a user session is open. Streamlit fragments are used for timed refreshes so the whole dashboard does not rerun every few seconds. The app labels the quote source and timestamp.

- Yahoo Finance / `yfinance` provides current NSE quote information and intraday history; Yahoo Finance's exchange-delay table lists NSE data as real-time.
- The verification screen also calls NSE's public quote endpoint when reachable and compares the two values. If the sources disagree beyond the tolerance, the app shows `REVIEW` instead of silently choosing a value.
- A professional deployment requiring tick-by-tick/order-book guarantees should use a licensed exchange data feed. NSE offers paid real-time feeds; broker APIs such as Upstox expose real-time WebSocket market data with authenticated access tokens.

## 2. Scheduled analytics layer

GitHub Actions refreshes historical daily prices, financial snapshots and news metadata on a weekday schedule. The refreshed CSV + SQLite files are committed back to GitHub for reproducibility and downstream dashboard analysis.

## 3. News corroboration

The news ETL combines several independent feeds: Economic Times, Moneycontrol, Business Standard, LiveMint, Financial Express, BusinessLine and Google News discovery. Headlines are mapped to the company universe, deduplicated, lightly classified by event/sentiment keywords, and clustered so the dashboard can display how many distinct sources covered a similar story.

The app stores headline metadata and links, not full article text. Publisher terms should be respected; some RSS feeds explicitly restrict use to personal/non-commercial display or require licensing for broader redistribution.

## v3 UI architecture

The public Streamlit application now separates the visitor experience into:

1. **Live Market** — current quote cards and a refreshable watchlist.
2. **Stock & Volume** — separate candlestick/price and volume charts.
3. **Technical Graphics** — RSI, MACD, signal-balance, moving averages, Bollinger Bands, ATR and relative volume.
4. **Analyst Chat** — a deterministic dashboard copilot grounded in the current data tables and live quote function.

The chatbot is deliberately keyless. It is a structured data assistant rather than a general-purpose LLM, so public visitors do not need an API key and responses can be traced back to the dashboard's current data.
