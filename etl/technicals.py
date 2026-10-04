"""Technical-analysis calculations shared by the dashboard and tests."""
from __future__ import annotations

import numpy as np
import pandas as pd


def technicals(hist: pd.DataFrame) -> pd.DataFrame:
    if hist.empty:
        return hist
    x = hist.copy()
    for col in ["Close", "High", "Low", "Open", "Volume"]:
        if col in x.columns:
            x[col.lower()] = pd.to_numeric(x[col], errors="coerce")
    x["sma20"] = x["close"].rolling(20).mean()
    x["sma50"] = x["close"].rolling(50).mean()
    x["sma200"] = x["close"].rolling(200).mean()
    delta = x["close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain / loss
    x["rsi14"] = 100 - (100 / (1 + rs))
    x.loc[(loss == 0) & (gain > 0), "rsi14"] = 100
    x.loc[(gain == 0) & (loss > 0), "rsi14"] = 0
    x.loc[(gain == 0) & (loss == 0), "rsi14"] = 50
    ema12 = x["close"].ewm(span=12, adjust=False).mean()
    ema26 = x["close"].ewm(span=26, adjust=False).mean()
    x["macd"] = ema12 - ema26
    x["macd_signal"] = x["macd"].ewm(span=9, adjust=False).mean()
    x["macd_hist"] = x["macd"] - x["macd_signal"]
    mid = x["close"].rolling(20).mean()
    x["bb_mid"] = mid
    std = x["close"].rolling(20).std()
    x["bb_upper"] = mid + 2 * std
    x["bb_lower"] = mid - 2 * std
    prev_close = x["close"].shift(1)
    true_range = pd.concat(
        [x["high"] - x["low"], (x["high"] - prev_close).abs(), (x["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    x["atr14"] = true_range.rolling(14).mean()
    x["volume_sma20"] = x["volume"].rolling(20).mean()
    x["relative_volume"] = x["volume"] / x["volume_sma20"].replace(0, np.nan)
    return x


def technical_snapshot(tech: pd.DataFrame) -> dict:
    if tech.empty:
        return {}
    x = tech.dropna(subset=["close"]).iloc[-1]
    out = {
        "close": float(x["close"]),
        "rsi": float(x["rsi14"]) if pd.notna(x["rsi14"]) else np.nan,
        "macd": float(x["macd"]) if pd.notna(x["macd"]) else np.nan,
        "macd_signal": float(x["macd_signal"]) if pd.notna(x["macd_signal"]) else np.nan,
        "sma20": float(x["sma20"]) if pd.notna(x["sma20"]) else np.nan,
        "sma50": float(x["sma50"]) if pd.notna(x["sma50"]) else np.nan,
        "sma200": float(x["sma200"]) if pd.notna(x["sma200"]) else np.nan,
        "atr14": float(x["atr14"]) if pd.notna(x["atr14"]) else np.nan,
        "relative_volume": float(x["relative_volume"]) if pd.notna(x["relative_volume"]) else np.nan,
    }
    bull = sum([
        pd.notna(out["rsi"]) and out["rsi"] > 55,
        pd.notna(out["macd"]) and pd.notna(out["macd_signal"]) and out["macd"] > out["macd_signal"],
        pd.notna(out["sma20"]) and out["close"] > out["sma20"],
        pd.notna(out["sma50"]) and out["close"] > out["sma50"],
        pd.notna(out["relative_volume"]) and out["relative_volume"] > 1,
    ])
    bear = sum([
        pd.notna(out["rsi"]) and out["rsi"] < 45,
        pd.notna(out["macd"]) and pd.notna(out["macd_signal"]) and out["macd"] < out["macd_signal"],
        pd.notna(out["sma20"]) and out["close"] < out["sma20"],
        pd.notna(out["sma50"]) and out["close"] < out["sma50"],
        pd.notna(out["relative_volume"]) and out["relative_volume"] < 0.8,
    ])
    out["bull_votes"] = bull
    out["bear_votes"] = bear
    out["read"] = "Bullish bias" if bull >= 3 else "Bearish bias" if bear >= 3 else "Mixed / watch"
    return out
