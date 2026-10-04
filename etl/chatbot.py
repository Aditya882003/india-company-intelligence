"""Deterministic data-aware analyst chatbot for the public dashboard."""
from __future__ import annotations

import pandas as pd


def _fmt_pct(v):
    return "N/A" if pd.isna(v) else f"{float(v):+.2f}%"


def _find_company(query: str, companies: pd.DataFrame):
    q = query.lower()
    hits = []
    for _, row in companies.iterrows():
        names = [str(row.get("company_name", "")), str(row.get("ticker", "")).replace(".NS", "")]
        names += [x.strip() for x in str(row.get("aliases", "")).split("|") if x.strip()]
        score = max((len(n) for n in names if n and n.lower() in q), default=0)
        if score:
            hits.append((score, row))
    return max(hits, key=lambda x: x[0])[1] if hits else None


def answer_query(query, companies, scored, prices, financials, news, live_quote_fn=None):
    q = query.strip().lower()
    if not q:
        return "Ask me about a company, live price, return, volatility, attention score, financials, sector performance, or recent news."

    if any(k in q for k in ("top attention", "highest attention", "most attention", "look first")):
        rows = scored.sort_values(["attention_score", "return_30d"], ascending=[False, True]).head(5)
        return "Top research-priority companies:\n" + "\n".join(
            f"• {r['company_name']}: score {int(r['attention_score'])}, {r['attention_flag']}, 30D {_fmt_pct(r['return_30d'])}."
            for _, r in rows.iterrows()
        )

    if "best 30" in q or "highest return" in q or "top return" in q:
        rows = scored.sort_values("return_30d", ascending=False).head(5)
        return "Top 30-day performers:\n" + "\n".join(
            f"• {r['company_name']}: {_fmt_pct(r['return_30d'])}" for _, r in rows.iterrows()
        )

    if "worst 30" in q or "lowest return" in q or "top losers" in q:
        rows = scored.sort_values("return_30d", ascending=True).head(5)
        return "Weakest 30-day performers:\n" + "\n".join(
            f"• {r['company_name']}: {_fmt_pct(r['return_30d'])}" for _, r in rows.iterrows()
        )

    if "sector" in q and any(k in q for k in ("best", "top", "performing")):
        rows = scored.groupby("sector", as_index=False)["return_30d"].mean().sort_values("return_30d", ascending=False).head(5)
        return "Best sectors by average 30-day return:\n" + "\n".join(
            f"• {r['sector']}: {_fmt_pct(r['return_30d'])}" for _, r in rows.iterrows()
        )

    company = _find_company(q, companies)
    if company is None:
        return "I could not identify a company. Try: ‘What is HDFC Bank's live price?’, ‘Why is Reliance high attention?’, or ‘Show Tata Motors recent news’."

    ticker = str(company["ticker"])
    name = str(company["company_name"])
    rows = scored[scored["ticker"] == ticker]
    if rows.empty:
        return f"I found {name}, but its analytics row is unavailable."
    row = rows.iloc[0]

    if any(k in q for k in ("price", "ltp", "quote", "trading at", "live")) and live_quote_fn:
        live = live_quote_fn(ticker)
        if live.get("price") is not None:
            change = live.get("pct_change")
            out = f"{name} latest available quote: ₹{float(live['price']):,.2f}"
            if change is not None:
                out += f" ({float(change):+.2f}% today)."
            out += f"\nSource: {live.get('source','market data')}. Timestamp: {live.get('timestamp_utc','N/A')}."
            return out
        return f"Fresh quote retrieval for {name} is unavailable right now."

    if any(k in q for k in ("news", "headline", "what happened", "recent")):
        nw = news[news["ticker"] == ticker].copy() if not news.empty else pd.DataFrame()
        if nw.empty:
            return f"No stored recent headlines were found for {name}."
        nw["published_dt"] = pd.to_datetime(nw["published_at"], errors="coerce", utc=True)
        nw = nw.sort_values("published_dt", ascending=False).head(5)
        return f"Recent {name} coverage:\n" + "\n".join(
            f"• {n.get('publisher') or n.get('source')}: {n.get('title','Untitled')}" for _, n in nw.iterrows()
        )

    if any(k in q for k in ("revenue", "profit", "margin", "roe", "financial", "debt")):
        f = financials[financials["ticker"] == ticker].sort_values("as_of_date", ascending=False).head(1)
        if f.empty:
            return f"No financial snapshot is available for {name}."
        f = f.iloc[0]
        return (f"{name}: revenue growth {_fmt_pct(f['revenue_growth_pct'])}, profit growth {_fmt_pct(f['profit_growth_pct'])}, "
                f"net margin {_fmt_pct(f['net_margin_pct'])}, ROE {_fmt_pct(f['roe_pct'])}.")

    return (f"{name} is {row['attention_flag']} attention (score {int(row['attention_score'])}).\n"
            f"30D return {_fmt_pct(row['return_30d'])}; volatility {_fmt_pct(row['volatility_30d'])}; "
            f"90D drawdown {_fmt_pct(row['max_drawdown_90d'])}.\n"
            f"News / 7D: {int(row.get('news_7d', 0))}; corroborated: {int(row.get('corroborated_7d', 0))}.")


SUGGESTED_PROMPTS = [
    "What is HDFC Bank's live price?",
    "Which companies have the highest attention score?",
    "Why is Reliance high attention?",
    "Show Tata Motors recent news",
    "Which sector has the best 30D return?",
]
