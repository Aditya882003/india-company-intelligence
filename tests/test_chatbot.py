import pandas as pd

from etl.chatbot import answer_query


def _frames():
    companies = pd.DataFrame([{
        "company_name": "HDFC Bank", "ticker": "HDFCBANK.NS", "sector": "Financials",
        "industry": "Private Banks", "aliases": "HDFC Bank|HDFC",
    }])
    scored = pd.DataFrame([{
        "company_name": "HDFC Bank", "ticker": "HDFCBANK.NS", "sector": "Financials",
        "return_30d": 6.2, "volatility_30d": 20.5, "max_drawdown_90d": -4.1,
        "revenue_growth_pct": 12.0, "profit_growth_pct": 8.0,
        "attention_score": 3, "attention_flag": "MEDIUM", "news_7d": 4, "corroborated_7d": 2,
    }])
    prices = pd.DataFrame()
    financials = pd.DataFrame([{
        "ticker": "HDFCBANK.NS", "as_of_date": "2026-06-30", "revenue": 1.2e12,
        "revenue_growth_pct": 12.0, "profit_growth_pct": 8.0, "net_margin_pct": 16.0, "roe_pct": 14.5,
    }])
    news = pd.DataFrame()
    return companies, scored, prices, financials, news


def test_chatbot_company_summary():
    ans = answer_query("Why is HDFC Bank high attention?", *_frames())
    assert "HDFC Bank" in ans
    assert "30D return" in ans


def test_chatbot_screening():
    ans = answer_query("Which companies have the highest attention score?", *_frames())
    assert "Top research-priority companies" in ans
