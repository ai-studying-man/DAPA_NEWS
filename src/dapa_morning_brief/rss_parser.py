from __future__ import annotations

import email.utils
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from dapa_morning_brief.models import Article, Section
from dapa_morning_brief.sources import (
    DEFENSE_BUSINESS_KEYWORDS,
    DEFENSE_ANCHOR_KEYWORDS,
    DEFENSE_CONTEXT_KEYWORDS,
    EXCLUDE_KEYWORDS,
    FOREIGN_CONTEXT_KEYWORDS,
    GENERIC_WEAPON_KEYWORDS,
    GOVERNMENT_ACTOR_KEYWORDS,
    KOREA_ANCHOR_KEYWORDS,
    POLICY_KEYWORDS,
    RELEVANT_KEYWORDS,
    WEAPON_SYSTEM_KEYWORDS,
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
    root = ET.fromstring(xml_text)
    cutoff = now - timedelta(days=days)
    articles: list[Article] = []

    for item in root.findall(".//item"):
        title = _text(item, "title")
        link = _text(item, "link")
        published_at = _parse_date(_text(item, "pubDate"))
        if not title or not link or published_at is None or published_at < cutoff:
            continue
        if not is_relevant_title(title):
            continue
        if default_section is Section.GOVERNMENT and not _is_current_government_news(
            title.casefold(),
        ):
            continue
        section = default_section or classify_title(title)
        source = _source_from_item(item) or source_name
        articles.append(
            Article(
                title=_clean_title(title),
                url=link,
                published_at=published_at,
                source=source,
                section=section,
            ),
        )

    return articles


def classify_title(title: str) -> Section:
    """Classify an article title into the closest newsletter section."""
    text = title.casefold()
    if _contains_any(text, EXCLUDE_KEYWORDS):
        return Section.POLICY
    if _is_current_government_news(text):
        return Section.GOVERNMENT
    if _is_weapon_system_news(text):
        return Section.WEAPON_SYSTEM
    if _contains_any(text, DEFENSE_BUSINESS_KEYWORDS):
        return Section.EXPORT_BUSINESS
    return Section.POLICY


def is_relevant_title(title: str) -> bool:
    """Return whether a title is relevant enough for DAPA morning brief."""
    text = title.casefold()
    if _contains_any(text, EXCLUDE_KEYWORDS):
        return False
    if _contains_any(text, FOREIGN_CONTEXT_KEYWORDS) and not _contains_any(
        text,
        KOREA_ANCHOR_KEYWORDS,
    ):
        return False
    if _is_current_government_news(text):
        return True
    if _contains_any(text, POLICY_KEYWORDS):
        return True
    if _is_weapon_system_news(text):
        return True
    return _contains_any(text, DEFENSE_BUSINESS_KEYWORDS)


def _is_current_government_news(text: str) -> bool:
    return _contains_any(text, GOVERNMENT_ACTOR_KEYWORDS) and _contains_any(
        text,
        DEFENSE_CONTEXT_KEYWORDS,
    )


def _is_weapon_system_news(text: str) -> bool:
    if not _contains_any(text, WEAPON_SYSTEM_KEYWORDS):
        return False
    specific_weapon_keywords = tuple(
        keyword
        for keyword in WEAPON_SYSTEM_KEYWORDS
        if keyword not in GENERIC_WEAPON_KEYWORDS
    )
    if _contains_any(text, specific_weapon_keywords) and (
        _contains_any(text, KOREA_ANCHOR_KEYWORDS)
        or _contains_any(text, DEFENSE_BUSINESS_KEYWORDS)
    ):
        return True
    if _contains_any(text, GENERIC_WEAPON_KEYWORDS):
        return _contains_any(text, DEFENSE_ANCHOR_KEYWORDS) or _contains_any(
            text,
            DEFENSE_BUSINESS_KEYWORDS,
        )
    return True


def _text(item: ET.Element, name: str) -> str:
    found = item.find(name)
    if found is None or found.text is None:
        return ""
    return found.text.strip()


def _source_from_item(item: ET.Element) -> str:
    for child in item:
        if child.tag.endswith("source") and child.text:
            return child.text.strip()
    return ""


def _parse_date(raw: str) -> datetime | None:
    if not raw:
        return None
    parsed = email.utils.parsedate_to_datetime(raw)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _clean_title(title: str) -> str:
    return re.sub(r"\s+", " ", title).strip()


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    return any(needle.casefold() in text for needle in needles)
