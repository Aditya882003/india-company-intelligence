from __future__ import annotations

import pandas as pd

from etl.metrics import transform_prices
from etl.news_sources import _sentiment, _event_type


def test_transform_prices_creates_expected_metrics():
    dates = pd.date_range("2026-01-01", periods=80, freq="B")
    rows = []
    for ticker, base in [("A.NS", 100.0), ("B.NS", 200.0)]:
        for i, d in enumerate(dates):
            close = base + i * 0.2
            rows.append({"ticker": ticker, "trade_date": d.strftime("%Y-%m-%d"), "open": close, "high": close, "low": close, "close": close, "volume": 1000+i})
    out = transform_prices(pd.DataFrame(rows))
    assert {"return_30d", "volatility_30d", "max_drawdown_90d", "market_score"}.issubset(out.columns)
    assert out["return_30d"].notna().sum() > 0


def test_news_signal_tags_are_deterministic():
    assert _sentiment("Company profit growth beats estimates", "") == "Positive"
    assert _sentiment("Regulator probe after major loss", "") == "Negative"
    assert _event_type("Company announces acquisition", "") == "M&A / Deal"
    assert _event_type("Board appoints new CEO", "") == "Management"
