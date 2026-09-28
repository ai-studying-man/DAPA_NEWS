"""Parse and classify RSS article metadata."""

from __future__ import annotations

import logging
import os
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, time, timedelta, timezone

from dapa_morning_brief.article_classification import (
    classify_title,
    is_current_government_news,
    is_relevant_article,
    is_relevant_title,
)
from dapa_morning_brief.models import Article, Section
from dapa_morning_brief.rss_metadata import (
    _clean_description,
    _clean_title,
    _parse_date,
    _source_from_item,
    _text,
    _view_count_from_item,
)

__all__ = [
    "KST",
    "MAX_RSS_CHARACTERS",
    "SEND_WINDOW_START",
    "classify_title",
    "is_relevant_article",
    "is_relevant_title",
    "parse_rss_items",
]

KST = timezone(timedelta(hours=9))
SEND_WINDOW_START = time(hour=6, minute=30, tzinfo=KST)
MAX_RSS_CHARACTERS = 5_000_000
_LOGGER = logging.getLogger(__name__)


def _trace_decision(decision: str, title: str, published_at: datetime | None) -> None:
    if os.environ.get("DAPA_NEWS_TRACE") != "1":
        return
    _LOGGER.setLevel(logging.INFO)
    _LOGGER.info(
        "candidate_parse decision=%s published_at=%s title=%s",
        decision,
        published_at.isoformat() if published_at is not None else "unknown",
        " ".join(title.split()),
    )


def parse_rss_items(
    xml_text: str,
    *,
    source_name: str,
    default_section: Section | None,
    days: int,
    now: datetime,
) -> list[Article]:
    """Parse RSS XML into article metadata."""
    if len(xml_text) > MAX_RSS_CHARACTERS:
        msg = "RSS response exceeds the parser size limit"
        raise ValueError(msg)

    # ElementTree does not resolve external entities; input size is bounded above.
    root = ET.fromstring(xml_text)  # noqa: S314
    cutoff = _freshness_cutoff(now, days=days)
    articles: list[Article] = []

    for feed_rank, item in enumerate(root.findall(".//item")):
        title = _text(item, "title")
        link = _text(item, "link")
        description = _clean_description(_text(item, "description"))
        source = _source_from_item(item) or source_name
        published_at = _parse_date(_text(item, "pubDate"))
        if not title or not link or published_at is None:
            _trace_decision("missing_metadata", title, published_at)
            continue
        if published_at < cutoff:
            _trace_decision("stale", title, published_at)
            continue
        if not is_relevant_article(title, description, source):
            _trace_decision("irrelevant", title, published_at)
            continue
        metadata_text = f"{title} {description}".casefold()
        if default_section is Section.GOVERNMENT and not is_current_government_news(
            metadata_text,
            title,
            source,
        ):
            _trace_decision("irrelevant", title, published_at)
            continue
        section = default_section or classify_title(
            title,
            description=description,
            source=source,
        )
        if section is None:
            _trace_decision("unclassified", title, published_at)
            continue
        articles.append(
            Article(
                title=_clean_title(title, source=source),
                url=link,
                published_at=published_at,
                source=source,
                section=section,
                description=description,
                view_count=_view_count_from_item(item),
                feed_rank=feed_rank,
            ),
        )
        _trace_decision("accepted", title, published_at)

    return articles


def _freshness_cutoff(now: datetime, *, days: int) -> datetime:
    kst_now = now.astimezone(KST)
    send_anchor = datetime.combine(kst_now.date(), SEND_WINDOW_START)
    return (send_anchor - timedelta(days=days)).astimezone(UTC)
