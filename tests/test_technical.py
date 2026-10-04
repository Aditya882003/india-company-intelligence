import pandas as pd

from etl.technicals import technical_snapshot, technicals


def test_technical_indicators_and_snapshot():
    periods = 260
    idx = pd.date_range("2026-01-01", periods=periods, freq="h", tz="UTC")
    base = pd.Series(range(periods), dtype=float) + 100
    df = pd.DataFrame({
        "Datetime": idx,
        "Open": base,
        "High": base + 2,
        "Low": base - 2,
        "Close": base + 1,
        "Volume": 100000 + (base * 10),
    })
    tech = technicals(df)
    expected = {"sma20", "sma50", "sma200", "rsi14", "macd", "macd_signal", "macd_hist", "atr14", "relative_volume"}
    assert expected.issubset(tech.columns)
    snap = technical_snapshot(tech)
    assert snap["close"] > 0
    assert 0 <= snap["rsi"] <= 100
    assert snap["relative_volume"] > 0
