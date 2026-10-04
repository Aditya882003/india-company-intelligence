from __future__ import annotations

import numpy as np
import pandas as pd

def transform_prices(prices: pd.DataFrame) -> pd.DataFrame:
    if prices.empty:
        return prices
    df = prices.copy().sort_values(["ticker", "trade_date"])
    grp = df.groupby("ticker", group_keys=False)
    df["return_30d"] = grp["close"].pct_change(30) * 100
    daily_returns = grp["close"].pct_change()
    df["volatility_30d"] = daily_returns.groupby(df["ticker"]).rolling(30).std().reset_index(level=0, drop=True) * np.sqrt(252) * 100
    rolling_high = grp["close"].rolling(90, min_periods=1).max().reset_index(level=0, drop=True)
    df["max_drawdown_90d"] = (df["close"] / rolling_high - 1) * 100
    df["market_score"] = (
        np.where(df["return_30d"] < -10, 2, np.where(df["return_30d"] < -5, 1, 0))
        + np.where(df["volatility_30d"] > 40, 2, np.where(df["volatility_30d"] > 25, 1, 0))
        + np.where(df["max_drawdown_90d"] < -20, 2, np.where(df["max_drawdown_90d"] < -10, 1, 0))
    )
    return df
