"""Rebuild the SQLite database from the current repository CSVs without calling external services."""
from __future__ import annotations

import sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "processed" / "company_intelligence.db"
SCHEMA = ROOT / "sql" / "schema.sql"
RAW = ROOT / "data" / "raw"


def main():
    master = pd.read_csv(ROOT / "data" / "company_master.csv")
    prices = pd.read_csv(RAW / "price_daily.csv") if (RAW / "price_daily.csv").exists() else pd.DataFrame()
    financials = pd.read_csv(RAW / "financial_snapshot.csv") if (RAW / "financial_snapshot.csv").exists() else pd.DataFrame()
    news = pd.read_csv(RAW / "news_articles.csv") if (RAW / "news_articles.csv").exists() else pd.DataFrame()
    for col, default in {
        "source": "Unknown", "company_name": "", "summary": "", "sentiment": "Neutral",
        "event_type": "General Market", "coverage_count": 1, "corroboration": "Single source"
    }.items():
        if col not in news.columns:
            news[col] = default
    if "company_name" not in news.columns and "ticker" in news.columns:
        news = news.merge(master[["ticker", "company_name"]], on="ticker", how="left")
    with sqlite3.connect(DB) as conn:
        conn.executescript("DROP TABLE IF EXISTS company_master; DROP TABLE IF EXISTS price_daily; DROP TABLE IF EXISTS financial_snapshot; DROP TABLE IF EXISTS news_articles; DROP TABLE IF EXISTS etl_run_log;")
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        master.to_sql("company_master", conn, if_exists="replace", index=False)
        prices.to_sql("price_daily", conn, if_exists="replace", index=False)
        financials.to_sql("financial_snapshot", conn, if_exists="replace", index=False)
        news.to_sql("news_articles", conn, if_exists="replace", index=False)
    print({"companies": len(master), "price_rows": len(prices), "financial_rows": len(financials), "news_rows": len(news)})


if __name__ == "__main__":
    main()
