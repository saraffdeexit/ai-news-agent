"""
fetch_news.py

Pulls recent AI-related headlines from Google News RSS for a set of
rotating queries, dedupes them, and returns a clean list of articles
from the last N days.

No API key required — Google News exposes a public RSS search endpoint.
"""

import urllib.parse
import datetime as dt
from dataclasses import dataclass, asdict

import feedparser

# Queries covering model releases, infra/compute bottlenecks, funding,
# regulation, and talent. Edit this list to tune what the digest covers.
QUERIES = [
    "AI chip shortage OR GPU supply",
    "AI compute bottleneck",
    "data center power AI",
    "AI regulation OR AI policy",
    "foundation model release OR launch",
    "NVIDIA OR OpenAI OR Anthropic OR \"Google DeepMind\"",
    "AI funding round OR valuation",
    "AI talent OR AI researcher hire",
]

LOOKBACK_DAYS = 7
MAX_PER_QUERY = 12


@dataclass
class Article:
    title: str
    link: str
    source: str
    published: str  # ISO 8601
    query: str


def _rss_url(query: str) -> str:
    q = urllib.parse.quote(query)
    # hl/gl/ceid pin results to English / US; adjust if you want other locales.
    return f"https://news.google.com/rss/search?q={q}+when:{LOOKBACK_DAYS}d&hl=en-US&gl=US&ceid=US:en"


def fetch_articles() -> list[Article]:
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=LOOKBACK_DAYS)
    seen_titles: set[str] = set()
    articles: list[Article] = []

    for query in QUERIES:
        feed = feedparser.parse(_rss_url(query))
        count = 0
        for entry in feed.entries:
            if count >= MAX_PER_QUERY:
                break

            title = entry.get("title", "").strip()
            if not title:
                continue

            # crude dedupe: normalize title, skip near-duplicates across queries
            key = title.lower()[:80]
            if key in seen_titles:
                continue

            published = entry.get("published", "")
            try:
                published_dt = dt.datetime(*entry.published_parsed[:6], tzinfo=dt.timezone.utc)
                if published_dt < cutoff:
                    continue
                published_iso = published_dt.isoformat()
            except Exception:
                published_iso = published

            source = ""
            if "source" in entry and hasattr(entry.source, "title"):
                source = entry.source.title
            elif " - " in title:
                source = title.rsplit(" - ", 1)[-1]

            seen_titles.add(key)
            articles.append(
                Article(
                    title=title,
                    link=entry.get("link", ""),
                    source=source,
                    published=published_iso,
                    query=query,
                )
            )
            count += 1

    return articles


if __name__ == "__main__":
    import json

    results = fetch_articles()
    print(f"Fetched {len(results)} articles across {len(QUERIES)} queries")
    print(json.dumps([asdict(a) for a in results[:5]], indent=2))
