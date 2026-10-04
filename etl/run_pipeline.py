"""Refresh the company-intelligence dataset.

No API key is required. Price and statement data come through yfinance; headline discovery
uses Google News RSS. The pipeline is designed to fail safely: if one company/source fails,
other companies can still refresh, while the run log records errors.
"""
from __future__ import annotations
import math

import argparse
import json
import logging
import sqlite3
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "company_master.csv"
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
DB = PROCESSED / "company_intelligence.db"
SCHEMA = ROOT / "sql" / "schema.sql"

RAW.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
LOG = logging.getLogger("india_company_intelligence")


def load_master() -> pd.DataFrame:
    return pd.read_csv(MASTER)


def flatten_yf_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    return df


def fetch_prices(tickers: list[str], period: str) -> tuple[pd.DataFrame, list[str]]:
    rows = []
    errors: list[str] = []
    for ticker in tickers:
        try:
            data = yf.download(
                ticker,
                period=period,
                interval="1d",
                auto_adjust=False,
                progress=False,
                threads=False,
                timeout=30,
            )
            if data.empty:
                raise ValueError("empty price response")
            data = flatten_yf_columns(data).reset_index()
            date_col = "Date" if "Date" in data.columns else "Datetime"
            data = data.rename(columns={
                date_col: "trade_date",
                "Open": "open", "High": "high", "Low": "low",
                "Close": "close", "Volume": "volume",
            })
            cols = ["trade_date", "open", "high", "low", "close", "volume"]
            data = data[[c for c in cols if c in data.columns]].copy()
            data["trade_date"] = pd.to_datetime(data["trade_date"], utc=True, errors="coerce").dt.tz_convert(None).dt.strftime("%Y-%m-%d")
            data["ticker"] = ticker
            for c in ["open", "high", "low", "close", "volume"]:
                if c in data.columns:
                    data[c] = pd.to_numeric(data[c], errors="coerce")
            data = data.dropna(subset=["trade_date", "close"])
            rows.append(data)
            LOG.info("price refresh: %s (%d rows)", ticker, len(data))
        except Exception as exc:
            msg = f"price {ticker}: {exc}"
            LOG.warning(msg)
            errors.append(msg)
        time.sleep(0.2)
    if not rows:
        return pd.DataFrame(columns=["ticker","trade_date","open","high","low","close","volume"]), errors
    return pd.concat(rows, ignore_index=True), errors


def _get_value(frame: pd.DataFrame | None, names: list[str], col) -> float:
    if frame is None or frame.empty:
        return np.nan
    for name in names:
        if name in frame.index:
            val = frame.loc[name, col]
            if isinstance(val, pd.Series):
                val = val.iloc[0]
            return pd.to_numeric(val, errors="coerce")
    return np.nan


def fetch_financials(tickers: list[str], financial_sectors: dict[str, str]) -> tuple[pd.DataFrame, list[str]]:
    rows = []
    errors: list[str] = []
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            inc = t.income_stmt
            bs = t.balance_sheet
            if inc is None or inc.empty:
                raise ValueError("empty income statement")
            cols = list(inc.columns)
            current = cols[0]
            previous = cols[1] if len(cols) > 1 else None
            revenue = _get_value(inc, ["Total Revenue", "Operating Revenue"], current)
            profit = _get_value(inc, ["Net Income", "Net Income Common Stockholders"], current)
            prev_rev = _get_value(inc, ["Total Revenue", "Operating Revenue"], previous) if previous is not None else np.nan
            prev_profit = _get_value(inc, ["Net Income", "Net Income Common Stockholders"], previous) if previous is not None else np.nan
            equity = _get_value(bs, ["Stockholders Equity", "Total Equity Gross Minority Interest"], current)
            debt = _get_value(bs, ["Total Debt", "Long Term Debt"], current)
            de = np.nan if financial_sectors.get(ticker) == "Financials" else (debt / equity if pd.notna(debt) and pd.notna(equity) and equity != 0 else np.nan)
            revenue_growth = ((revenue / prev_rev) - 1) * 100 if pd.notna(revenue) and pd.notna(prev_rev) and prev_rev != 0 else np.nan
            profit_growth = ((profit / prev_profit) - 1) * 100 if pd.notna(profit) and pd.notna(prev_profit) and prev_profit != 0 else np.nan
            margin = (profit / revenue) * 100 if pd.notna(profit) and pd.notna(revenue) and revenue != 0 else np.nan
            roe = (profit / equity) * 100 if pd.notna(profit) and pd.notna(equity) and equity != 0 else np.nan
            rows.append({
                "ticker": ticker,
                "as_of_date": pd.Timestamp(current).date().isoformat(),
                "fiscal_period": pd.Timestamp(current).date().isoformat(),
                "revenue": revenue,
                "net_income": profit,
                "revenue_growth_pct": revenue_growth,
                "profit_growth_pct": profit_growth,
                "net_margin_pct": margin,
                "debt_equity": de,
                "roe_pct": roe,
                "source": "Yahoo Finance public data interface via yfinance",
            })
            LOG.info("financial refresh: %s", ticker)
        except Exception as exc:
            msg = f"financial {ticker}: {exc}"
            LOG.warning(msg)
            errors.append(msg)
        time.sleep(0.35)
    return pd.DataFrame(rows), errors


from etl.metrics import transform_prices
from etl.news_sources import fetch_multi_source_news

def fetch_news(master: pd.DataFrame, per_company: int = 50) -> tuple[pd.DataFrame, list[str]]:
    return fetch_multi_source_news(master, max_per_company=per_company)


def save_csvs(master: pd.DataFrame, prices: pd.DataFrame, financials: pd.DataFrame, news: pd.DataFrame) -> None:
    master.to_csv(ROOT / "data" / "company_master.csv", index=False)
    prices.to_csv(RAW / "price_daily.csv", index=False)
    financials.to_csv(RAW / "financial_snapshot.csv", index=False)
    news.to_csv(RAW / "news_articles.csv", index=False)


def save_database(master: pd.DataFrame, prices: pd.DataFrame, financials: pd.DataFrame, news: pd.DataFrame, run_log: dict) -> None:
    with sqlite3.connect(DB) as conn:
        conn.executescript("""
            DROP TABLE IF EXISTS company_master;
            DROP TABLE IF EXISTS price_daily;
            DROP TABLE IF EXISTS financial_snapshot;
            DROP TABLE IF EXISTS news_articles;
            DROP TABLE IF EXISTS etl_run_log;
        """)
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        master.to_sql("company_master", conn, if_exists="replace", index=False)
        prices.to_sql("price_daily", conn, if_exists="replace", index=False)
        financials.to_sql("financial_snapshot", conn, if_exists="replace", index=False)
        news.to_sql("news_articles", conn, if_exists="replace", index=False)
        pd.DataFrame([run_log]).to_sql("etl_run_log", conn, if_exists="append", index=False)


def read_existing(path: Path, cols: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=cols)
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame(columns=cols)


def merge_fallback(live: pd.DataFrame, existing: pd.DataFrame, key: str) -> pd.DataFrame:
    if live.empty:
        return existing
    if existing.empty:
        return live
    live_keys = set(live[key].dropna().astype(str))
    keep_existing = existing[~existing[key].astype(str).isin(live_keys)]
    return pd.concat([live, keep_existing], ignore_index=True)


def main(period: str, skip_news: bool = False) -> int:
    started = datetime.now(timezone.utc)
    master = load_master()
    sector_map = master.set_index("ticker")["sector"].to_dict()
    tickers = master["ticker"].dropna().tolist()

    prices_live, p_err = fetch_prices(tickers, period)
    prices_live = transform_prices(prices_live)
    existing_prices = read_existing(RAW / "price_daily.csv", ["ticker","trade_date","open","high","low","close","volume"])
    existing_prices = transform_prices(existing_prices)
    prices = merge_fallback(prices_live, existing_prices, "ticker")
    prices = transform_prices(prices)

    fin_live, f_err = fetch_financials(tickers, sector_map)
    existing_fin = read_existing(RAW / "financial_snapshot.csv", list(fin_live.columns) if not fin_live.empty else ["ticker","as_of_date","fiscal_period","revenue","net_income","revenue_growth_pct","profit_growth_pct","net_margin_pct","debt_equity","roe_pct","source"])
    financials = merge_fallback(fin_live, existing_fin, "ticker")

    if skip_news:
        news = read_existing(RAW / "news_articles.csv", ["ticker","published_at","title","publisher","link","guid"])
        n_err = []
    else:
        news_live, n_err = fetch_news(master)
        existing_news = read_existing(RAW / "news_articles.csv", ["ticker","published_at","title","publisher","link","guid"])
        news = pd.concat([news_live, existing_news], ignore_index=True).drop_duplicates(subset=["guid"], keep="first")
        if len(news) > 1000:
            news["published_at_dt"] = pd.to_datetime(news["published_at"], errors="coerce", utc=True)
            news = news.sort_values("published_at_dt", ascending=False).groupby("ticker").head(50).drop(columns=["published_at_dt"])

    errors = p_err + f_err + n_err
    status = "SUCCESS" if not errors else ("PARTIAL" if len(errors) < len(tickers) * 0.5 else "DEGRADED")
    if prices.empty or prices["ticker"].nunique() < max(3, math.ceil(len(tickers) * 0.3)):
        status = "FAILED"

    log = {
        "run_ts_utc": started.isoformat(),
        "status": status,
        "company_count": len(master),
        "price_rows": len(prices),
        "financial_rows": len(financials),
        "news_rows": len(news),
        "error_count": len(errors),
        "notes": json.dumps(errors[:20]),
    }
    if status != "FAILED":
        save_csvs(master, prices, financials, news)
        save_database(master, prices, financials, news, log)
    print(json.dumps(log, indent=2))
    return 0 if status != "FAILED" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default="1y", choices=["6mo", "1y", "2y", "5y"])
    parser.add_argument("--skip-news", action="store_true")
    args = parser.parse_args()
    raise SystemExit(main(args.period, args.skip_news))
