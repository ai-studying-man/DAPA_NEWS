"""Collect DAPA-related articles from configured RSS sources."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import quote_plus

import httpx

from dapa_morning_brief.rss_parser import (
    classify_title,
    is_relevant_title,
    parse_rss_items,
)

if TYPE_CHECKING:
    from dapa_morning_brief.models import Article
from dapa_morning_brief.sources import (
    AGENCY_QUERY,
    BROAD_FALLBACK_QUERY,
    RSS_SOURCES,
    SECTION_QUERIES,
    SINGLE_FALLBACK_KEYWORDS,
    USER_AGENT,
)

__all__ = [
    "build_google_news_rss_url",
    "classify_title",
    "collect_articles",
    "is_relevant_title",
]


def collect_articles(
    *,
    days: int,
    include_google: bool,
    only_google: bool,
) -> list[Article]:
    """Collect articles from official RSS and optional Google News RSS."""
    now = datetime.now(UTC)
    timeout = httpx.Timeout(connect=5.0, read=20.0, write=5.0, pool=5.0)
    headers = {"User-Agent": os.getenv("DAPA_BRIEF_USER_AGENT", USER_AGENT)}
    collected: list[Article] = []

    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers=headers,
    ) as client:
        if not only_google:
            collected.extend(_collect_official_rss(client, days=days, now=now))
        if include_google or only_google:
            collected.extend(_collect_google_by_section(client, days=days, now=now))
        if not collected:
            collected.extend(
                _collect_google_query(client, BROAD_FALLBACK_QUERY, days, now),
            )
        if not collected:
            for keyword in SINGLE_FALLBACK_KEYWORDS:
                collected.extend(_collect_google_query(client, keyword, days, now))
                if collected:
                    break

    return collected


def build_google_news_rss_url(query: str, *, days: int = 1) -> str:
    """Build a Korean Google News RSS search URL."""
    encoded = quote_plus(f"({query}) when:{days}d")
    return (
        "https://news.google.com/rss/search"
        f"?q={encoded}&hl=ko&gl=KR&ceid=KR:ko"
    )


def _collect_official_rss(
    client: httpx.Client,
    *,
    days: int,
    now: datetime,
) -> list[Article]:
    collected: list[Article] = []
    for source in RSS_SOURCES:
        try:
            response = client.get(source.url)
            _ = response.raise_for_status()
            collected.extend(
                parse_rss_items(
                    response.text,
                    source_name=source.name,
                    default_section=source.default_section,
                    days=days,
                    now=now,
                ),
            )
        except (httpx.HTTPError, ET.ParseError, ValueError):
            continue
    return collected


def _collect_google_by_section(
    client: httpx.Client,
    *,
    days: int,
    now: datetime,
) -> list[Article]:
    articles = _collect_google_query(client, AGENCY_QUERY, days, now)
    for query in SECTION_QUERIES.values():
        articles.extend(_collect_google_query(client, query, days, now))
    return articles


def _collect_google_query(
    client: httpx.Client,
    query: str,
    days: int,
    now: datetime,
) -> list[Article]:
    url = build_google_news_rss_url(query, days=days)
    try:
        response = client.get(url)
        _ = response.raise_for_status()
        return parse_rss_items(
            response.text,
            source_name="Google News",
            default_section=None,
            days=days,
            now=now,
        )
    except (httpx.HTTPError, ET.ParseError, ValueError):
        return []
