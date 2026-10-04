from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
from etl.metrics import transform_prices


def test_transform_prices_creates_metrics():
    dates = pd.bdate_range('2026-01-01', periods=100)
    rows = []
    for i, d in enumerate(dates):
        rows.append({'ticker':'TEST.NS','trade_date':d.strftime('%Y-%m-%d'),'open':100+i,'high':101+i,'low':99+i,'close':100+i,'volume':1000})
    out = transform_prices(pd.DataFrame(rows))
    assert {'return_30d','volatility_30d','max_drawdown_90d','market_score'}.issubset(out.columns)
    assert len(out) == 100


def test_master_has_indian_companies():
    df = pd.read_csv(ROOT / 'data' / 'company_master.csv')
    assert len(df) >= 20
    assert df['ticker'].str.endswith('.NS').all()
    assert df['sector'].notna().all()
