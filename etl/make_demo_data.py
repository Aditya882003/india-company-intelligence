"""Create deterministic seed data so the dashboard works before the first live refresh."""
from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd
import random

ROOT = Path(__file__).resolve().parents[1]
MASTER = pd.read_csv(ROOT / 'data' / 'company_master.csv')
RAW = ROOT / 'data' / 'raw'
DB = ROOT / 'data' / 'processed' / 'company_intelligence.db'
SCHEMA = ROOT / 'sql' / 'schema.sql'
RAW.mkdir(parents=True, exist_ok=True)
DB.parent.mkdir(parents=True, exist_ok=True)
if DB.exists():
    DB.unlink()

random.seed(42)
rng = np.random.default_rng(42)
dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=260)
price_rows = []
for i, r in MASTER.iterrows():
    base = 700 + (i * 37) % 900
    drift = rng.normal(0.00025, 0.001)
    shocks = rng.normal(0, 0.012, len(dates))
    # Give a few companies realistic stress / outperformance regimes.
    if i % 7 == 0:
        shocks[-35:] += -0.0025
    if i % 9 == 0:
        shocks[-25:] += 0.0020
    close = base * np.exp(np.cumsum(drift + shocks))
    for j, dt in enumerate(dates):
        c = float(close[j])
        o = float(c * (1 + rng.normal(0, 0.004)))
        h = max(o, c) * (1 + abs(rng.normal(0, 0.006)))
        l = min(o, c) * (1 - abs(rng.normal(0, 0.006)))
        v = int(abs(rng.normal(3_000_000, 800_000)))
        price_rows.append([r.ticker, dt.strftime('%Y-%m-%d'), o, h, l, c, v])
prices = pd.DataFrame(price_rows, columns=['ticker','trade_date','open','high','low','close','volume'])
prices = prices.sort_values(['ticker','trade_date'])
prices['return_30d'] = prices.groupby('ticker')['close'].pct_change(30) * 100
prices['volatility_30d'] = prices.groupby('ticker')['close'].pct_change().groupby(prices['ticker']).rolling(30).std().reset_index(level=0, drop=True) * np.sqrt(252) * 100
rolling = prices.groupby('ticker')['close'].rolling(90, min_periods=1).max().reset_index(level=0, drop=True)
prices['max_drawdown_90d'] = (prices['close'] / rolling - 1) * 100
prices['market_score'] = (
    np.where(prices['return_30d'] < -10, 2, np.where(prices['return_30d'] < -5, 1, 0))
    + np.where(prices['volatility_30d'] > 40, 2, np.where(prices['volatility_30d'] > 25, 1, 0))
    + np.where(prices['max_drawdown_90d'] < -20, 2, np.where(prices['max_drawdown_90d'] < -10, 1, 0))
)

fin_rows = []
for i, r in MASTER.iterrows():
    revenue = 50_000 + i * 2700 + rng.normal(0, 1300)
    prev_revenue = revenue / (1 + rng.uniform(-0.05, 0.20))
    profit = revenue * rng.uniform(0.05, 0.22)
    prev_profit = profit / (1 + rng.uniform(-0.10, 0.30))
    equity = revenue * rng.uniform(0.4, 1.4)
    debt = equity * rng.uniform(0.1, 2.2)
    if r.sector == 'Financials':
        de = np.nan
    else:
        de = debt / equity
    fin_rows.append({
        'ticker': r.ticker, 'as_of_date': dates[-1].strftime('%Y-%m-%d'), 'fiscal_period': dates[-1].strftime('%Y-%m-%d'),
        'revenue': revenue, 'net_income': profit,
        'revenue_growth_pct': (revenue / prev_revenue - 1) * 100,
        'profit_growth_pct': (profit / prev_profit - 1) * 100,
        'net_margin_pct': profit / revenue * 100,
        'debt_equity': de, 'roe_pct': profit / equity * 100,
        'source': 'DEMO SEED DATA - replace via ETL'
    })
financials = pd.DataFrame(fin_rows)
news = pd.DataFrame(columns=['ticker','published_at','title','publisher','link','guid'])
master = MASTER.copy()

prices.to_csv(RAW/'price_daily.csv', index=False)
financials.to_csv(RAW/'financial_snapshot.csv', index=False)
news.to_csv(RAW/'news_articles.csv', index=False)
with sqlite3.connect(DB) as conn:
    conn.executescript(SCHEMA.read_text())
    master.to_sql('company_master', conn, if_exists='replace', index=False)
    prices.to_sql('price_daily', conn, if_exists='replace', index=False)
    financials.to_sql('financial_snapshot', conn, if_exists='replace', index=False)
    news.to_sql('news_articles', conn, if_exists='replace', index=False)
    pd.DataFrame([{
        'run_ts_utc': pd.Timestamp.now(tz='UTC').isoformat(), 'status':'DEMO', 'company_count':len(master),
        'price_rows':len(prices),'financial_rows':len(financials),'news_rows':0,'error_count':0,'notes':'Seed data only'
    }]).to_sql('etl_run_log', conn, if_exists='append', index=False)
print('Demo data created:', len(master), 'companies;', len(prices), 'price rows')
