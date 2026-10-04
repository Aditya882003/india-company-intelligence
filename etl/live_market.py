"""Live market layer for the public dashboard.

The dashboard separates this short-lived live layer from the scheduled historical ETL:
- Yahoo Finance / yfinance is used for current NSE quotes and intraday history.
- NSE's public quote endpoint is used as an independent exchange-side verification when reachable.

The app should label a quote with the source and timestamp rather than claiming an exchange feed
when the exchange verification endpoint is unavailable.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
import requests
import yfinance as yf

NSE_BASE = "https://www.nseindia.com"
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/149 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/market-data/live-equity-market",
    "Connection": "keep-alive",
}


def _float(value: Any) -> float | None:
    try:
        x = float(value)
        return x if np.isfinite(x) else None
    except Exception:
        return None


def fetch_yahoo_quote(ticker: str) -> dict[str, Any]:
    """Fetch a current quote snapshot and source timestamp from Yahoo Finance."""
    t = yf.Ticker(ticker)
    info = {}
    try:
        info = dict(t.fast_info)
    except Exception:
        info = {}
    last = _float(info.get("last_price"))
    prev = _float(info.get("previous_close"))
    day_high = _float(info.get("day_high"))
    day_low = _float(info.get("day_low"))
    volume = _float(info.get("last_volume"))
    last_trade_time = info.get("last_trade_time")

    # A 1-minute history fallback is more robust if fast_info lacks one of the fields.
    intraday = pd.DataFrame()
    if last is None or last_trade_time is None:
        try:
            intraday = t.history(period="1d", interval="1m", auto_adjust=False, prepost=False)
            if not intraday.empty:
                last_row = intraday.dropna(subset=["Close"]).iloc[-1]
                last = last or _float(last_row.get("Close"))
                if prev is None:
                    hist_prev = t.history(period="5d", interval="1d", auto_adjust=False)
                    if len(hist_prev) >= 2:
                        prev = _float(hist_prev["Close"].iloc[-2])
                day_high = day_high or _float(intraday["High"].max())
                day_low = day_low or _float(intraday["Low"].min())
                volume = volume or _float(intraday["Volume"].sum())
                last_trade_time = intraday.index[-1]
        except Exception:
            pass

    change = (last - prev) if last is not None and prev is not None else None
    pct_change = (change / prev * 100) if change is not None and prev not in (None, 0) else None
    ts = pd.to_datetime(last_trade_time, utc=True, errors="coerce") if last_trade_time is not None else pd.NaT
    if pd.isna(ts):
        ts = pd.Timestamp.now(tz="UTC")

    return {
        "ticker": ticker,
        "source": "Yahoo Finance / yfinance",
        "price": last,
        "previous_close": prev,
        "change": change,
        "pct_change": pct_change,
        "day_high": day_high,
        "day_low": day_low,
        "volume": volume,
        "timestamp_utc": ts.isoformat(),
        "status": "OK" if last is not None else "ERROR",
    }


def _nse_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(NSE_HEADERS)
    try:
        s.get(NSE_BASE, timeout=12)
    except requests.RequestException:
        pass
    return s


def fetch_nse_quote(nse_symbol: str) -> dict[str, Any]:
    """Fetch the current public NSE quote for verification.

    NSE may reject automated requests; the caller should treat an error here as a verification
    source being unavailable, not as a market-data failure.
    """
    s = _nse_session()
    url = f"{NSE_BASE}/api/quote-equity?symbol={quote_plus(nse_symbol)}"
    try:
        r = s.get(url, timeout=15)
        r.raise_for_status()
        payload = r.json()
        pi = payload.get("priceInfo", {}) or {}
        day = pi.get("intraDayHighLow", {}) or {}
        last = _float(pi.get("lastPrice"))
        prev = _float(pi.get("previousClose"))
        return {
            "symbol": nse_symbol,
            "source": "NSE India",
            "price": last,
            "previous_close": prev,
            "change": (last - prev) if last is not None and prev is not None else _float(pi.get("change")),
            "pct_change": _float(pi.get("pChange")),
            "day_high": _float(day.get("max")),
            "day_low": _float(day.get("min")),
            "volume": _float((payload.get("marketDeptOrderBook") or {}).get("totalTradedVolume")),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "status": "OK" if last is not None else "ERROR",
        }
    except Exception as exc:
        return {
            "symbol": nse_symbol,
            "source": "NSE India",
            "price": None,
            "previous_close": None,
            "change": None,
            "pct_change": None,
            "day_high": None,
            "day_low": None,
            "volume": None,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "status": f"UNAVAILABLE: {type(exc).__name__}",
        }


def verify_quote(ticker: str, nse_symbol: str | None = None) -> dict[str, Any]:
    yahoo = fetch_yahoo_quote(ticker)
    nse = fetch_nse_quote(nse_symbol or ticker.replace(".NS", ""))
    y = yahoo.get("price")
    n = nse.get("price")
    if y is not None and n is not None:
        diff = abs(y - n)
        diff_pct = diff / n * 100 if n else None
        if diff_pct is not None and diff_pct <= 0.15:
            verdict = "MATCH"
        else:
            verdict = "REVIEW"
    elif y is not None:
        diff = None
        diff_pct = None
        verdict = "YAHOO_ONLY"
    else:
        diff = None
        diff_pct = None
        verdict = "NO_QUOTE"
    return {
        "yahoo": yahoo,
        "nse": nse,
        "difference": diff,
        "difference_pct": diff_pct,
        "verdict": verdict,
    }


def fetch_live_board(tickers: list[str], max_workers: int = 6) -> pd.DataFrame:
    """Fetch a modest live board in parallel to reduce dashboard latency."""
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(fetch_yahoo_quote, t): t for t in tickers}
        for fut in as_completed(futs):
            try:
                rows.append(fut.result())
            except Exception as exc:
                rows.append({"ticker": futs[fut], "source": "Yahoo Finance / yfinance", "status": f"ERROR: {type(exc).__name__}"})
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("pct_change", ascending=False, na_position="last")


def fetch_intraday(ticker: str, period: str = "1d", interval: str = "1m") -> pd.DataFrame:
    """Return intraday OHLCV for the selected security."""
    t = yf.Ticker(ticker)
    df = t.history(period=period, interval=interval, auto_adjust=False, prepost=False)
    if df.empty:
        return pd.DataFrame()
    df = df.reset_index()
    time_col = "Datetime" if "Datetime" in df.columns else "Date"
    df[time_col] = pd.to_datetime(df[time_col], utc=True, errors="coerce")
    return df
