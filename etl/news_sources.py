"""Multi-source Indian business/market news discovery and corroboration."""
from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import quote_plus

import pandas as pd
import requests

NEWS_SOURCES = {
    "Economic Times": "https://economictimes.indiatimes.com/rssfeedsdefault.cms",
    "Moneycontrol": "https://www.moneycontrol.com/rss/latestnews.xml",
    "Business Standard": "https://www.business-standard.com/rss/markets-106.rss",
    "LiveMint": "https://www.livemint.com/rss/companies",
    "Financial Express": "https://www.financialexpress.com/market/feed/",
    "BusinessLine": "https://www.thehindubusinessline.com/feeder/default.rss",
    "Google News": "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en",
}

POSITIVE_WORDS = {
    "beats", "beat", "growth", "grows", "surge", "surges", "upgrade", "upgraded", "approval",
    "approved", "order win", "contract", "expansion", "acquisition", "buyback", "dividend", "launch",
    "partnership", "record", "profit", "guidance raised", "strong demand", "capacity addition",
}
NEGATIVE_WORDS = {
    "loss", "losses", "downgrade", "downgraded", "probe", "investigation", "penalty", "default", "fraud",
    "resign", "resigned", "weak demand", "decline", "falls", "fall", "drop", "drops", "lawsuit", "ban",
    "delay", "warning", "debt", "rating cut", "guidance cut", "fire", "recall", "regulatory action",
}
EVENT_RULES = [
    ("Earnings", ["earnings", "results", "profit", "revenue", "ebitda", "quarter"]),
    ("M&A / Deal", ["acquire", "acquisition", "merger", "stake", "deal", "partnership"]),
    ("Regulatory", ["sebi", "rbi", "regulator", "probe", "penalty", "ban", "approval", "court"]),
    ("Management", ["ceo", "cfo", "md", "resign", "appointed", "board"]),
    ("Capital / Corporate Action", ["buyback", "dividend", "bonus", "split", "fundraise", "qip"]),
    ("Operations", ["order", "contract", "plant", "capacity", "production", "launch"]),
]

HEADERS = {"User-Agent": "IndiaCompanyIntelligence/2.0 (research dashboard; headline metadata only)"}


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def _sentiment(title: str, summary: str) -> str:
    text = (title + " " + summary).lower()
    p = sum(1 for w in POSITIVE_WORDS if w in text)
    n = sum(1 for w in NEGATIVE_WORDS if w in text)
    if p > n:
        return "Positive"
    if n > p:
        return "Negative"
    return "Neutral"


def _event_type(title: str, summary: str) -> str:
    text = (title + " " + summary).lower()
    for label, keys in EVENT_RULES:
        if any(k in text for k in keys):
            return label
    return "General Market"


def _parse_feed(xml_text: str, source: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    rows: list[dict] = []
    for item in root.findall(".//item"):
        title = _clean(item.findtext("title") or "")
        link = _clean(item.findtext("link") or "")
        guid = _clean(item.findtext("guid") or link or title)
        summary = _clean(item.findtext("description") or "")
        pub = _clean(item.findtext("pubDate") or item.findtext("published") or "")
        publisher_el = item.find("source")
        publisher = _clean(publisher_el.text) if publisher_el is not None and publisher_el.text else source
        if not title:
            continue
        rows.append({
            "source": source,
            "publisher": publisher,
            "published_at": pub,
            "title": title,
            "summary": summary[:500],
            "link": link,
            "guid": guid,
            "sentiment": _sentiment(title, summary),
            "event_type": _event_type(title, summary),
        })
    return rows


def _aliases(row: pd.Series) -> list[str]:
    values = [str(row.get("company_name", ""))]
    alias_blob = row.get("aliases", "")
    if pd.notna(alias_blob) and str(alias_blob).strip():
        values.extend([x.strip() for x in str(alias_blob).split("|") if x.strip()])
    return sorted(set(v for v in values if v), key=len, reverse=True)


def fetch_multi_source_news(master: pd.DataFrame, max_per_company: int = 50) -> tuple[pd.DataFrame, list[str]]:
    """Fetch headlines across multiple independent feeds and map them to companies by aliases."""
    raw: list[dict] = []
    errors: list[str] = []
    for source, url in NEWS_SOURCES.items():
        try:
            if "{query}" in url:
                # Search queries are handled company-by-company below; skip in this pass.
                continue
            r = requests.get(url, headers=HEADERS, timeout=18)
            r.raise_for_status()
            raw.extend(_parse_feed(r.text, source))
        except Exception as exc:
            errors.append(f"news source {source}: {type(exc).__name__}: {exc}")
        time.sleep(0.15)

    # Add Google News search results for each company as a discovery source.
    for _, row in master.iterrows():
        company = str(row["company_name"])
        query = quote_plus(f'"{company}" India stock')
        url = NEWS_SOURCES["Google News"].format(query=query)
        try:
            r = requests.get(url, headers=HEADERS, timeout=18)
            r.raise_for_status()
            parsed = _parse_feed(r.text, "Google News")
            for p in parsed[:20]:
                p["matched_query"] = company
            raw.extend(parsed[:20])
        except Exception as exc:
            errors.append(f"news source Google News/{company}: {type(exc).__name__}: {exc}")
        time.sleep(0.1)

    if not raw:
        return pd.DataFrame(columns=[
            "ticker", "company_name", "source", "publisher", "published_at", "title", "summary",
            "link", "guid", "sentiment", "event_type", "coverage_count", "corroboration"
        ]), errors

    all_news = pd.DataFrame(raw).drop_duplicates(subset=["guid"], keep="first")
    # Match every article to all companies whose alias appears in title/summary.
    mapped: list[dict] = []
    for _, article in all_news.iterrows():
        hay = f"{article.get('title','')} {article.get('summary','')}".lower()
        for _, company in master.iterrows():
            aliases = _aliases(company)
            if any(alias.lower() in hay for alias in aliases):
                item = article.to_dict()
                item["ticker"] = company["ticker"]
                item["company_name"] = company["company_name"]
                mapped.append(item)

    if not mapped:
        return pd.DataFrame(columns=[
            "ticker", "company_name", "source", "publisher", "published_at", "title", "summary",
            "link", "guid", "sentiment", "event_type", "coverage_count", "corroboration"
        ]), errors

    df = pd.DataFrame(mapped)
    # Cluster near-identical headlines to estimate corroboration.
    def norm_title(s: str) -> str:
        return re.sub(r"[^a-z0-9 ]+", "", s.lower()).strip()

    normalized = df["title"].map(norm_title)
    cluster_id = {}
    cluster = 0
    seen: dict[str, int] = {}
    for idx, title in normalized.items():
        key = " ".join(sorted(set(title.split())))
        assigned = None
        for old_key, cid in seen.items():
            a, b = set(key.split()), set(old_key.split())
            if a and b and len(a & b) / max(1, len(a | b)) >= 0.55:
                assigned = cid
                break
        if assigned is None:
            assigned = cluster
            seen[key] = assigned
            cluster += 1
        cluster_id[idx] = assigned
    df["cluster_id"] = pd.Series(cluster_id)
    coverage = df.groupby(["ticker", "cluster_id"])["source"].transform("nunique")
    df["coverage_count"] = coverage.astype(int)
    df["corroboration"] = df["coverage_count"].map(lambda x: f"{x} sources" if x > 1 else "Single source")
    df = df.sort_values("published_at", ascending=False).groupby("ticker").head(max_per_company)
    return df.drop(columns=["cluster_id"], errors="ignore"), errors
