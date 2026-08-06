"""Parse and classify RSS article metadata."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, time, timedelta, timezone
from typing import TYPE_CHECKING

from dapa_morning_brief.business_rules import (
    DEFENSE_INDUSTRY_KEYWORDS,
    contains_defense_anchor,
    is_defense_business_news,
    is_defense_export_news,
)
from dapa_morning_brief.government_rules import (
    CURRENT_DEFENSE_LEADER_KEYWORDS,
    CURRENT_GOVERNMENT_LEADER_KEYWORDS,
    CURRENT_GOVERNMENT_NARRATIVE_KEYWORDS,
    CURRENT_GOVERNMENT_POLICY_KEYWORDS,
    GENERAL_GOVERNMENT_POLICY_KEYWORDS,
    current_government_actor,
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
from dapa_morning_brief.sources import (
    AGENCY_KEYWORDS,
    DEFENSE_TECH_KEYWORDS,
    DOMESTIC_WEAPON_PROGRAM_KEYWORDS,
    EXCLUDE_KEYWORDS,
    FOREIGN_CONTEXT_KEYWORDS,
    GENERIC_WEAPON_KEYWORDS,
    KOREA_ANCHOR_KEYWORDS,
    POLICY_KEYWORDS,
    UNTRUSTED_SOURCE_KEYWORDS,
    UNTRUSTED_TITLE_PREFIXES,
    WEAPON_SYSTEM_KEYWORDS,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

KST = timezone(timedelta(hours=9))
SEND_WINDOW_START = time(hour=6, minute=30, tzinfo=KST)
MAX_RSS_CHARACTERS = 5_000_000


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
        if not title or not link or published_at is None or published_at < cutoff:
            continue
        if not is_relevant_article(title, description, source):
            continue
        metadata_text = f"{title} {description} {source}".casefold()
        if default_section is Section.GOVERNMENT and not _is_current_government_news(
            metadata_text,
            title,
        ):
            continue
        section = default_section or classify_title(
            title,
            description=description,
            source=source,
        )
        articles.append(
            Article(
                title=_clean_title(title),
                url=link,
                published_at=published_at,
                source=source,
                section=section,
                description=description,
                view_count=_view_count_from_item(item),
                feed_rank=feed_rank,
            ),
        )

    return articles


def classify_title(
    title: str,
    *,
    description: str = "",
    source: str = "",
) -> Section:
    """Classify an article title into the closest newsletter section."""
    text = f"{title} {description} {source}".casefold()
    if _contains_any(text, EXCLUDE_KEYWORDS):
        section = Section.POLICY
    elif _is_current_government_news(text, title):
        section = Section.GOVERNMENT
    elif is_defense_export_news(text):
        section = Section.EXPORT_BUSINESS
    elif _is_defense_tech_policy_news(text):
        section = Section.POLICY
    elif _is_weapon_system_news(text):
        section = Section.WEAPON_SYSTEM
    elif _contains_any(text, POLICY_KEYWORDS):
        section = Section.POLICY
    elif is_defense_business_news(text):
        section = Section.EXPORT_BUSINESS
    else:
        section = Section.POLICY
    return section


def is_relevant_title(title: str) -> bool:
    """Return whether a title is relevant enough for DAPA morning brief."""
    return is_relevant_article(title, "", "")


def is_relevant_article(title: str, description: str, source: str) -> bool:
    """Return whether available RSS metadata is relevant to the brief."""
    text = f"{title} {description} {source}".casefold()
    normalized_title = title.strip().casefold()
    if normalized_title.startswith(UNTRUSTED_TITLE_PREFIXES) or _contains_any(
        source.casefold(),
        UNTRUSTED_SOURCE_KEYWORDS,
    ):
        return False
    if _contains_any(text, AGENCY_KEYWORDS):
        return True
    if _contains_any(text, EXCLUDE_KEYWORDS):
        return False
    defense_export = is_defense_export_news(text)
    if (
        _contains_any(text, FOREIGN_CONTEXT_KEYWORDS)
        and not _contains_any(text, KOREA_ANCHOR_KEYWORDS)
        and not defense_export
    ):
        return False
    return (
        _is_current_government_news(text, title)
        or _is_defense_tech_policy_news(text)
        or defense_export
        or _contains_any(text, POLICY_KEYWORDS)
        or _is_weapon_system_news(text)
        or is_defense_business_news(text)
    )


def _is_current_government_news(text: str, title: str) -> bool:
    if "국방부" in text:
        return True
    headline_actor = current_government_actor(title)
    named_current_leader = _contains_any(text, CURRENT_GOVERNMENT_LEADER_KEYWORDS)
    narrative_actor = _contains_any(text, CURRENT_GOVERNMENT_NARRATIVE_KEYWORDS)
    if headline_actor is None and not named_current_leader and not narrative_actor:
        return False
    defense_context = (
        _contains_any(text, POLICY_KEYWORDS)
        or is_defense_business_news(text)
        or _is_defense_tech_policy_news(text)
        or _is_weapon_system_news(text)
    )
    defense_leader_context = headline_actor in CURRENT_DEFENSE_LEADER_KEYWORDS and (
        _contains_any(text, WEAPON_SYSTEM_KEYWORDS)
    )
    generic_presidential_context = headline_actor in {"대통령", "대통령실"} and (
        _contains_any(text, CURRENT_GOVERNMENT_POLICY_KEYWORDS)
    )
    generic_government_context = headline_actor == "정부" and _contains_any(
        text,
        GENERAL_GOVERNMENT_POLICY_KEYWORDS,
    )
    return (
        defense_context
        or (
            named_current_leader
            and _contains_any(text, CURRENT_GOVERNMENT_POLICY_KEYWORDS)
        )
        or (narrative_actor and defense_context)
        or defense_leader_context
        or generic_presidential_context
        or generic_government_context
    )


def _freshness_cutoff(now: datetime, *, days: int) -> datetime:
    kst_now = now.astimezone(KST)
    send_anchor = datetime.combine(kst_now.date(), SEND_WINDOW_START)
    if kst_now < send_anchor:
        send_anchor -= timedelta(days=1)
    return (send_anchor - timedelta(days=days)).astimezone(UTC)


def _is_defense_tech_policy_news(text: str) -> bool:
    if not _contains_defense_tech_keyword(text):
        return False
    return contains_defense_anchor(text)


def _contains_defense_tech_keyword(text: str) -> bool:
    if re.search(r"(?<![a-z0-9])ai(?![a-z0-9])", text):
        return True
    return _contains_any(
        text,
        tuple(
            keyword for keyword in DEFENSE_TECH_KEYWORDS if keyword.casefold() != "ai"
        ),
    )


def _is_weapon_system_news(text: str) -> bool:
    if not _contains_any(text, WEAPON_SYSTEM_KEYWORDS):
        return False
    if _contains_any(text, DOMESTIC_WEAPON_PROGRAM_KEYWORDS):
        return True
    specific_weapon_keywords = tuple(
        keyword
        for keyword in WEAPON_SYSTEM_KEYWORDS
        if keyword not in GENERIC_WEAPON_KEYWORDS
    )
    if _contains_any(text, specific_weapon_keywords) and (
        _contains_any(text, KOREA_ANCHOR_KEYWORDS) or is_defense_business_news(text)
    ):
        return True
    if _contains_any(text, GENERIC_WEAPON_KEYWORDS):
        return contains_defense_anchor(text) or _contains_any(
            text,
            DEFENSE_INDUSTRY_KEYWORDS,
        )
    return False


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    return any(needle.casefold() in text for needle in needles)
