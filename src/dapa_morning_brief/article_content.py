"""Download selected news pages and extract their main article text."""

from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, timedelta
from functools import partial
from typing import TYPE_CHECKING, ClassVar, Final

import httpx
import trafilatura
from googlenewsdecoder import gnewsdecoder
from pydantic import BaseModel, ConfigDict, ValidationError

from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.models import PRACTICE_POINT_SECTIONS
from dapa_morning_brief.source_config import USER_AGENT

if TYPE_CHECKING:
    from collections.abc import Iterable

    from dapa_morning_brief.models import Article, Briefing

MAX_BODY_CHARACTERS: Final = 4_000
MIN_BODY_CHARACTERS: Final = 40
MAX_FETCH_WORKERS: Final = 8


class _DecodedGoogleUrl(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    status: bool
    decoded_url: str | None = None


@dataclass(frozen=True, slots=True)
class _FreshnessRejection:
    title: str
    source: str
    publisher_date: date


@dataclass(frozen=True, slots=True)
class _PublisherDateFilterResult:
    articles: tuple[Article, ...]
    checked_google: int
    rejected: tuple[_FreshnessRejection, ...]
    unverified_titles: tuple[str, ...]

    @property
    def unverifiable(self) -> int:
        return len(self.unverified_titles)


@dataclass(frozen=True, slots=True)
class _PublisherDateInspection:
    article: Article
    publisher_date: date | None


def extract_main_text(html_text: str) -> str | None:
    """Extract bounded article text from an HTML document."""
    extracted = trafilatura.extract(
        html_text,
        favor_precision=True,
        include_comments=False,
        include_tables=False,
        output_format="txt",
    )
    if extracted is None:
        return None
    normalized = " ".join(extracted.split())
    if len(normalized) < MIN_BODY_CHARACTERS:
        return None
    return normalized[:MAX_BODY_CHARACTERS]


def resolve_article_url(article_url: str) -> str:
    """Resolve Google News RSS links to their publisher URL when possible."""
    if not article_url.startswith("https://news.google.com/"):
        return article_url
    try:
        decoded = _DecodedGoogleUrl.model_validate(gnewsdecoder(article_url))
    except ValidationError:
        return article_url
    if decoded.status and decoded.decoded_url:
        return decoded.decoded_url
    return article_url


def _filter_articles_by_publisher_date(
    articles: Iterable[Article],
    *,
    as_of: date,
    max_age_days: int,
) -> _PublisherDateFilterResult:
    if max_age_days < 1:
        msg = "max_age_days must be at least 1"
        raise ValueError(msg)
    all_articles = tuple(articles)
    google_articles = tuple(
        article
        for article in all_articles
        if article.url.startswith("https://news.google.com/")
    )
    if not google_articles:
        return _PublisherDateFilterResult(
            articles=all_articles,
            checked_google=0,
            rejected=(),
            unverified_titles=(),
        )

    timeout = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)
    headers = {"User-Agent": os.getenv("DAPA_BRIEF_USER_AGENT", USER_AGENT)}
    with (
        httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers=headers,
        ) as client,
        ThreadPoolExecutor(
            max_workers=min(MAX_FETCH_WORKERS, len(google_articles)),
        ) as executor,
    ):
        inspections = tuple(
            executor.map(
                partial(_inspect_publisher_date, client),
                google_articles,
            ),
        )

    cutoff_date = as_of - timedelta(days=max_age_days)
    accepted_google: set[Article] = set()
    rejected: list[_FreshnessRejection] = []
    unverified_titles: list[str] = []
    for inspection in inspections:
        publisher_date = inspection.publisher_date
        if publisher_date is None:
            unverified_titles.append(inspection.article.title)
        elif cutoff_date <= publisher_date <= as_of:
            accepted_google.add(inspection.article)
        else:
            rejected.append(
                _FreshnessRejection(
                    title=inspection.article.title,
                    source=inspection.article.source,
                    publisher_date=publisher_date,
                ),
            )

    return _PublisherDateFilterResult(
        articles=tuple(
            article
            for article in all_articles
            if not article.url.startswith("https://news.google.com/")
            or article in accepted_google
        ),
        checked_google=len(google_articles),
        rejected=tuple(rejected),
        unverified_titles=tuple(unverified_titles),
    )


def _inspect_publisher_date(
    client: httpx.Client,
    article: Article,
) -> _PublisherDateInspection:
    resolved_url = resolve_article_url(article.url)
    if resolved_url.startswith("https://news.google.com/"):
        return _PublisherDateInspection(article=article, publisher_date=None)
    try:
        response = client.get(resolved_url)
        _ = response.raise_for_status()
    except httpx.HTTPError:
        return _PublisherDateInspection(article=article, publisher_date=None)
    metadata = trafilatura.extract_metadata(response.text)
    raw_date = metadata.date if metadata is not None else None
    return _PublisherDateInspection(
        article=article,
        publisher_date=_parse_publisher_date(raw_date),
    )


def _parse_publisher_date(raw_date: str | None) -> date | None:
    if raw_date is None:
        return None
    matched = re.match(r"^(\d{4}-\d{2}-\d{2})", raw_date.strip())
    if matched is None:
        return None
    try:
        return date.fromisoformat(matched.group(1))
    except ValueError:
        return None


def fetch_article_bodies(briefing: Briefing) -> tuple[ArticleBody, ...]:
    """Fetch article bodies concurrently while preserving briefing order."""
    timeout = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)
    headers = {"User-Agent": os.getenv("DAPA_BRIEF_USER_AGENT", USER_AGENT)}
    articles = tuple(
        article
        for section, section_articles in briefing.sections.items()
        if section in PRACTICE_POINT_SECTIONS
        for article in section_articles
    )
    if not articles:
        return ()
    with (
        httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers=headers,
        ) as client,
        ThreadPoolExecutor(
            max_workers=min(MAX_FETCH_WORKERS, len(articles)),
        ) as executor,
    ):
        fetched = executor.map(partial(_fetch_article_body, client), articles)
        return tuple(body for body in fetched if body is not None)


def _fetch_article_body(client: httpx.Client, article: Article) -> ArticleBody | None:
    try:
        response = client.get(resolve_article_url(article.url))
        _ = response.raise_for_status()
    except httpx.HTTPError:
        return None
    body = extract_main_text(response.text)
    if body is None:
        return None
    return ArticleBody(
        article_url=article.url,
        title=article.title,
        source=article.source,
        body=body,
    )
