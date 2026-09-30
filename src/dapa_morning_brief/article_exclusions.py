"""Rules for excluding disallowed publishers and fictional news content."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from dapa_morning_brief.models import Article

_BLOCKED_PUBLISHER_HOSTS = frozenset({"digitalchosun.dizzo.com"})
_BLOCKED_PUBLISHER_LABELS = (
    "조선일보",
    "조선비즈",
    "디지틀조선일보",
    "디지털조선일보",
)
_SERIAL_EPISODE_TITLE = re.compile(r"^\s*(?:\[\s*\d+\s*화\s*\]|제\s*\d+\s*화\b)")
_FICTIONAL_CONTENT = re.compile(
    r"""(?:
        웹\s*소설
        | 연재\s*소설
        | 장편\s*소설
        | 단편\s*소설
        | 픽션
        | fiction(?:al)?\b
        | 허구(?:의)?\s*(?:인물|캐릭터|등장인물|상황|사건|이야기|내용)
        | 가공의\s*(?:인물|캐릭터|등장인물)
        | 가상의?\s*(?:인물|캐릭터|등장인물)
        | 실존하지\s+않는\s*(?:인물|캐릭터|등장인물)
        | (?:소설|작품|이야기)\s*속\s*(?:인물|등장인물|주인공|상황|사건)?
        | 작중\s*(?:인물|등장인물|상황|사건)
        | 등장인물
        | (?:이야기|인물|사건|내용).{0,20}(?:허구|fiction)
    )""",
    re.VERBOSE,
)


def is_excluded_publisher(*, source: str, url: str) -> bool:
    """Identify Chosun publisher hosts and source labels."""
    hostname = (urlsplit(url).hostname or "").casefold().rstrip(".")
    if hostname == "chosun.com" or hostname.endswith(".chosun.com"):
        return True
    if hostname in _BLOCKED_PUBLISHER_HOSTS:
        return True
    source = source.casefold()
    return any(label.casefold() in source for label in _BLOCKED_PUBLISHER_LABELS)


def fiction_exclusion_reason(article: Article, body: str) -> str | None:
    """Return an exclusion reason for serial fiction or fictional content."""
    if _SERIAL_EPISODE_TITLE.search(article.title):
        return "serialized_episode"
    text = f"{article.title} {article.description} {body}".casefold()
    if _FICTIONAL_CONTENT.search(text):
        return "fictional_content"
    return None
