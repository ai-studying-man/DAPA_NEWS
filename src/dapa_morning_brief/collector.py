"""Collect candidates with bounded requests and observable source health."""

from __future__ import annotations

import logging
import os
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from functools import partial
from typing import TYPE_CHECKING
from urllib.parse import quote_plus

import httpx
from typing_extensions import override

from dapa_morning_brief.naver_news import NAVER_NEWS_URL, parse_naver_items
from dapa_morning_brief.naver_rate_limit import NaverRequestGate
from dapa_morning_brief.official_sources import BOARD_SOURCES, parse_board_articles
from dapa_morning_brief.rss_parser import (
    MAX_RSS_CHARACTERS,
    classify_title,
    is_relevant_title,
    parse_rss_items,
)
from dapa_morning_brief.source_config import (
    AGENCY_QUERY,
    BROAD_FALLBACK_QUERY,
    NAVER_SEARCH_QUERIES,
    RSS_SOURCES,
    SECTION_QUERIES,
    SINGLE_FALLBACK_KEYWORDS,
    USER_AGENT,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from dapa_morning_brief.models import Article

__all__ = [
    "CollectionError",
    "build_google_news_rss_url",
    "classify_title",
    "collect_articles",
    "is_relevant_title",
]
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CollectionError(RuntimeError):
    """Every configured collection request failed."""

    attempted: int

    @override
    def __str__(self) -> str:
        """Describe the collection outage without request credentials."""
        return f"All news sources failed ({self.attempted} requests); aborting"


@dataclass(frozen=True, slots=True)
class _FeedRequest:
    source: str
    url: str
    parser: Callable[[str], list[Article]]
    query: str = ""


@dataclass(frozen=True, slots=True)
class _FeedResult:
    articles: tuple[Article, ...]
    succeeded: bool


def collect_articles(
    *, days: int, include_google: bool, only_google: bool
) -> list[Article]:
    """Collect official sources plus enabled search providers, failing on outage."""
    now = datetime.now(UTC)
    requests: list[_FeedRequest] = []
    if not only_google:
        requests.extend(
            _FeedRequest(
                source.name,
                source.url,
                partial(
                    parse_rss_items,
                    source_name=source.name,
                    default_section=None,
                    days=days,
                    now=now,
                ),
            )
            for source in RSS_SOURCES
        )
        requests.extend(
            _FeedRequest(
                name,
                url,
                partial(parse_board_articles, parser=parser, days=days, now=now),
            )
            for name, url, parser in BOARD_SOURCES
        )
        if os.getenv("NAVER_CLIENT_ID") and os.getenv("NAVER_CLIENT_SECRET"):
            requests.extend(
                _FeedRequest(
                    "naver",
                    f"{NAVER_NEWS_URL}?query={quote_plus(query)}&display=100&sort=date",
                    partial(parse_naver_items, days=days, now=now),
                    query,
                )
                for query in NAVER_SEARCH_QUERIES
            )
        else:
            _LOGGER.warning(
                "news_source_skipped source=naver reason=missing_credentials"
            )
    if include_google or only_google:
        queries = (
            AGENCY_QUERY,
            *(q for values in SECTION_QUERIES.values() for q in values),
        )
        requests.extend(_google_request(query, days, now) for query in queries)
    timeout = httpx.Timeout(connect=5.0, read=20.0, write=5.0, pool=5.0)
    with (
        httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=6, max_keepalive_connections=6),
            headers={"User-Agent": os.getenv("DAPA_BRIEF_USER_AGENT", USER_AGENT)},
        ) as client,
        ThreadPoolExecutor(max_workers=6) as executor,
    ):
        fetch = partial(_fetch, client, NaverRequestGate())
        results = list(executor.map(fetch, requests))
        collected = [article for result in results for article in result.articles]
        if not collected and (include_google or only_google):
            fallback = [
                _google_request(q, days, now)
                for q in (
                    BROAD_FALLBACK_QUERY,
                    *SINGLE_FALLBACK_KEYWORDS,
                )
            ]
            results.extend(executor.map(fetch, fallback))
            collected = [article for result in results for article in result.articles]
    if results and not any(result.succeeded for result in results):
        raise CollectionError(attempted=len(results))
    _LOGGER.warning(
        "news_collection_complete requests=%d successful=%d accepted=%d",
        len(results),
        sum(result.succeeded for result in results),
        len(collected),
    )
    return collected


def build_google_news_rss_url(query: str, *, days: int = 1) -> str:
    """Build a Korean Google News RSS search URL."""
    encoded = quote_plus(f"({query}) when:{days}d")
    return f"https://news.google.com/rss/search?q={encoded}&hl=ko&gl=KR&ceid=KR:ko"


def _google_request(query: str, days: int, now: datetime) -> _FeedRequest:
    return _FeedRequest(
        "google",
        build_google_news_rss_url(query, days=days),
        partial(
            parse_rss_items,
            source_name="Google News",
            default_section=None,
            days=days,
            now=now,
        ),
        query,
    )


def _fetch(
    client: httpx.Client, naver_gate: NaverRequestGate, feed: _FeedRequest
) -> _FeedResult:
    try:
        response = (
            naver_gate.get(client, feed.url)
            if feed.source == "naver"
            else client.get(feed.url)
        )
        _ = response.raise_for_status()
        is_board = any(feed.url == url for _, url, _ in BOARD_SOURCES)
        if not is_board:
            received = _rss_item_count(response.text)
        else:
            received = len(re.findall(r"<tr\b", response.text, re.IGNORECASE))
        articles = feed.parser(response.text)
    except (httpx.HTTPError, ET.ParseError, ValueError) as error:
        status = (
            error.response.status_code
            if isinstance(error, httpx.HTTPStatusError)
            else None
        )
        _LOGGER.warning(
            "news_source_failed source=%s query=%s error=%s status=%s",
            feed.source,
            feed.query,
            type(error).__name__,
            status,
        )
        return _FeedResult((), succeeded=False)
    if feed.source == "google":
        articles = [replace(article, search_provider="google") for article in articles]
    _LOGGER.warning(
        "news_source_complete source=%s query=%s received_rows=%d accepted=%d",
        feed.source,
        feed.query,
        received,
        len(articles),
    )
    return _FeedResult(tuple(articles), succeeded=True)


def _rss_item_count(document: str) -> int:
    if len(document) > MAX_RSS_CHARACTERS:
        msg = "RSS response exceeds the parser size limit"
        raise ValueError(msg)
    root = ET.fromstring(document)  # noqa: S314
    if root.tag != "rss" or root.find("channel") is None:
        msg = "Expected RSS channel in source response"
        raise ValueError(msg)
    return len(root.findall(".//item"))
