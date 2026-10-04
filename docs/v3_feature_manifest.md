# v3 Feature Manifest

| Feature | What it does | Data path |
|---|---|---|
| Live quote | Refreshes selected-company quote during an active session | `etl/live_market.py` |
| Live watchlist | Fetches multiple current quotes in parallel | `etl/live_market.py` |
| Stock chart | Interactive OHLC candlestick + moving averages + Bollinger Bands | `etl/technicals.py` + Streamlit |
| Volume chart | Dedicated traded-volume chart + average volume | `etl/technicals.py` + Streamlit |
| RSI | 14-period momentum oscillator + gauge | `etl/technicals.py` |
| MACD | Histogram, MACD and signal lines | `etl/technicals.py` |
| ATR | 14-period volatility measure | `etl/technicals.py` |
| Relative volume | Current volume relative to 20-period average | `etl/technicals.py` |
| Analyst Copilot | Plain-English queries over dashboard data | `etl/chatbot.py` |
| Multi-source news | RSS/news discovery and corroboration | `etl/news_sources.py` |
| Source verification | Yahoo vs NSE public quote comparison | `etl/live_market.py` |
