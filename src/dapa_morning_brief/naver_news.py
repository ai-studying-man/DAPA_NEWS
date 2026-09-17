"""Normalize Naver's search RSS without trusting its ingestion timestamp."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import replace
from typing import TYPE_CHECKING, Final
from urllib.parse import urlsplit

from dapa_morning_brief.rss_metadata import _clean_description, _text
from dapa_morning_brief.rss_parser import MAX_RSS_CHARACTERS, parse_rss_items

if TYPE_CHECKING:
    from datetime import datetime

    from dapa_morning_brief.models import Article

NAVER_NEWS_URL: Final = "https://openapi.naver.com/v1/search/news.xml"


def parse_naver_items(xml_text: str, *, days: int, now: datetime) -> list[Article]:
    """Preserve publisher URLs and tag candidates for original-date verification."""
    if len(xml_text) > MAX_RSS_CHARACTERS:
        msg = "Naver response exceeds the parser size limit"
        raise ValueError(msg)
    root = ET.fromstring(xml_text)  # noqa: S314
    for item in root.findall(".//item"):
        link = item.find("link")
        original = _text(item, "originallink") or _text(item, "link")
        if link is not None:
            link.text = original
        for field in ("title", "description"):
            element = item.find(field)
            if element is not None:
                text = re.sub(r"</?b\b[^>]*>", "", "".join(element.itertext()))
                element.text = _clean_description(text)
                for child in list(element):
                    element.remove(child)
        ET.SubElement(item, "source").text = urlsplit(original).hostname or "Naver News"
    articles = parse_rss_items(
        ET.tostring(root, encoding="unicode"),
        source_name="Naver News",
        default_section=None,
        days=days,
        now=now,
    )
    return [replace(article, search_provider="naver") for article in articles]
