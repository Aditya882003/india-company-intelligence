PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS company_master (
    ticker TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    sector TEXT NOT NULL,
    industry TEXT NOT NULL,
    peer_group TEXT,
    business_summary TEXT,
    monitoring_theme TEXT,
    source_url TEXT,
    aliases TEXT
);

CREATE TABLE IF NOT EXISTS price_daily (
    ticker TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL,
    return_30d REAL,
    volatility_30d REAL,
    max_drawdown_90d REAL,
    market_score INTEGER,
    PRIMARY KEY (ticker, trade_date)
);

CREATE TABLE IF NOT EXISTS financial_snapshot (
    ticker TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    fiscal_period TEXT,
    revenue REAL,
    net_income REAL,
    revenue_growth_pct REAL,
    profit_growth_pct REAL,
    net_margin_pct REAL,
    debt_equity REAL,
    roe_pct REAL,
    source TEXT,
    PRIMARY KEY (ticker, as_of_date, fiscal_period)
);

CREATE TABLE IF NOT EXISTS news_articles (
    ticker TEXT NOT NULL,
    company_name TEXT,
    source TEXT,
    publisher TEXT,
    published_at TEXT,
    title TEXT NOT NULL,
    summary TEXT,
    link TEXT,
    guid TEXT PRIMARY KEY,
    sentiment TEXT,
    event_type TEXT,
    coverage_count INTEGER,
    corroboration TEXT
);

CREATE TABLE IF NOT EXISTS etl_run_log (
    run_ts_utc TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    company_count INTEGER,
    price_rows INTEGER,
    financial_rows INTEGER,
    news_rows INTEGER,
    error_count INTEGER,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_price_date ON price_daily(trade_date);
CREATE INDEX IF NOT EXISTS idx_news_ticker_date ON news_articles(ticker, published_at);
CREATE INDEX IF NOT EXISTS idx_news_source ON news_articles(source);
