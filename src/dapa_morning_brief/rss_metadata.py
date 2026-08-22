"""Extract and normalize metadata fields from RSS items."""

from __future__ import annotations

import email.utils
import html
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

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
    cleaned = re.sub(r"\s+", " ", html.unescape(title)).strip()
    return re.sub(
        r"\s*(?:[-|·]\s*)?\[?\s*(?:v\.daum\.net|(?:www\.)?newfilenews\.com)\s*\]?\s*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).rstrip()


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
