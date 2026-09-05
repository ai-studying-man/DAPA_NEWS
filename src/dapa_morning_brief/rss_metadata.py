"""Extract and normalize metadata fields from RSS items."""

from __future__ import annotations

import email.utils
import html
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    import xml.etree.ElementTree as ET

__all__ = [
    "_clean_description",
    "_clean_title",
    "_parse_date",
    "_source_from_item",
    "_text",
    "_view_count_from_item",
]

DOMAIN_PATTERN: Final[str] = r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,63}"
DOMAIN_SUFFIX_PATTERN: Final[re.Pattern[str]] = re.compile(
    "".join(
        (
            r"\s*(?:[-|·:\uFF1A]\s*|\[\s*)(?:https?://)?(?:www\.)?",
            rf"{DOMAIN_PATTERN}(?::\d+)?(?:[/#?][^\s\]]*)?\s*\]?\s*$",
        ),
    ),
    flags=re.IGNORECASE,
)


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


def _clean_title(title: str, *, source: str = "") -> str:
    cleaned = re.sub(r"\s+", " ", html.unescape(title)).strip()
    normalized_source = re.sub(r"\s+", " ", html.unescape(source)).strip()
    source_suffix_pattern = (
        re.compile(
            rf"\s*(?:[-|·:\uFF1A]\s*|\[\s*){re.escape(normalized_source)}\s*\]?\s*$",
            flags=re.IGNORECASE,
        )
        if normalized_source
        else None
    )
    previous = ""
    while cleaned != previous:
        previous = cleaned
        if source_suffix_pattern is not None:
            cleaned = source_suffix_pattern.sub("", cleaned).rstrip()
        cleaned = DOMAIN_SUFFIX_PATTERN.sub("", cleaned).rstrip()
    return cleaned


def _clean_description(description: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", description)
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def _view_count_from_item(item: ET.Element) -> int | None:
    view_tags = {"hits", "view_count", "viewcount", "views"}
    for child in item:
        local_name = child.tag.rsplit("}", maxsplit=1)[-1].casefold()
        if local_name not in view_tags or child.text is None:
            continue
        digits = re.sub(r"[^0-9]", "", child.text)
        if digits:
            return int(digits)
    return None
