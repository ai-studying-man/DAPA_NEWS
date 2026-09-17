"""Adapt existing official board parsers into topic-classified candidates."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING, Final

from dapa_morning_brief.models import Article
from dapa_morning_brief.official_press_releases import (
    parse_dapa_press_releases,
    parse_mnd_press_releases,
)
from dapa_morning_brief.rss_parser import KST, classify_title, is_relevant_article

if TYPE_CHECKING:
    from collections.abc import Callable

    from dapa_morning_brief.models import OfficialPressRelease

BOARD_SOURCES: Final = (
    (
        "방위사업청",
        "https://www.dapa.go.kr/dapa/doc/selectDocList.do?bbsSeq=326&menuSeq=3069",
        parse_dapa_press_releases,
    ),
    ("국방부", "https://www.mnd.go.kr/mnd/167/subview.do", parse_mnd_press_releases),
)


def parse_board_articles(
    document: str,
    *,
    parser: Callable[[str], tuple[OfficialPressRelease, ...]],
    days: int,
    now: datetime,
) -> list[Article]:
    """Use only dated current releases; date-only boards retain midnight precision."""
    releases = parser(document)
    if not releases:
        msg = "Official board has no recognizable dated rows"
        raise ValueError(msg)
    today = now.astimezone(KST).date()
    cutoff = today - timedelta(days=days)
    return [
        Article(
            title=release.title,
            url=release.url,
            published_at=datetime.combine(release.published_on, time.min, tzinfo=KST),
            source=release.agency,
            section=classify_title(release.title, source=release.agency),
        )
        for release in releases
        if cutoff <= release.published_on <= today
        and is_relevant_article(release.title, "", release.agency)
    ]
