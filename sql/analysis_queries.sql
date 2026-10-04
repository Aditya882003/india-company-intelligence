-- Latest market snapshot by company
WITH ranked AS (
  SELECT p.*, ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY trade_date DESC) AS rn
  FROM price_daily p
)
SELECT c.company_name, c.sector, r.trade_date, r.close, r.return_30d,
       r.volatility_30d, r.max_drawdown_90d, r.market_score
FROM ranked r
JOIN company_master c USING(ticker)
WHERE r.rn = 1
ORDER BY r.market_score DESC, r.return_30d ASC;

-- Sector risk / return view
WITH ranked AS (
  SELECT p.*, ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY trade_date DESC) AS rn
  FROM price_daily p
), latest AS (
  SELECT * FROM ranked WHERE rn = 1
)
SELECT c.sector,
       COUNT(*) AS companies,
       ROUND(AVG(l.return_30d), 2) AS avg_return_30d,
       ROUND(AVG(l.volatility_30d), 2) AS avg_volatility_30d,
       SUM(CASE WHEN l.market_score >= 4 THEN 1 ELSE 0 END) AS stressed_companies
FROM latest l
JOIN company_master c USING(ticker)
GROUP BY c.sector
ORDER BY avg_return_30d DESC;

-- Companies with negative momentum and weak latest growth
WITH ranked AS (
  SELECT f.*, ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY as_of_date DESC) AS rn
  FROM financial_snapshot f
), latest_f AS (
  SELECT * FROM ranked WHERE rn = 1
), ranked_p AS (
  SELECT p.*, ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY trade_date DESC) AS rn
  FROM price_daily p
), latest_p AS (
  SELECT * FROM ranked_p WHERE rn = 1
)
SELECT c.company_name, c.sector, lp.return_30d, lf.revenue_growth_pct,
       lf.profit_growth_pct, lf.net_margin_pct
FROM company_master c
JOIN latest_p lp USING(ticker)
LEFT JOIN latest_f lf USING(ticker)
WHERE lp.return_30d < 0
  AND (lf.revenue_growth_pct < 0 OR lf.profit_growth_pct < 0)
ORDER BY lp.return_30d ASC;

-- Recent news activity by company
SELECT c.company_name, c.sector, COUNT(*) AS headlines_7d
FROM news_articles n
JOIN company_master c USING(ticker)
WHERE datetime(n.published_at) >= datetime('now', '-7 days')
GROUP BY c.company_name, c.sector
ORDER BY headlines_7d DESC;
