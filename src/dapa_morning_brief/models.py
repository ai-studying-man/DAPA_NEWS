"""Domain models for collected articles and rendered briefings."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from datetime import date, datetime


class Section(StrEnum):
    """Newsletter section."""

    GOVERNMENT = "government"
    POLICY = "policy"
    WEAPON_SYSTEM = "weapon_system"
    EXPORT_BUSINESS = "export_business"

    @property
    def display_title(self) -> str:
        """Return the Korean section heading."""
        return SECTION_DISPLAY_TITLES[self]


SECTION_DISPLAY_TITLES: Final[dict[Section, str]] = {
    Section.GOVERNMENT: "현 정부 / 국방부 주요 뉴스",
    Section.POLICY: "방위사업 관련 동향",
    Section.WEAPON_SYSTEM: "무기체계·전력화",
    Section.EXPORT_BUSINESS: "방산수출·기업동향",
}


@dataclass(frozen=True, slots=True)
class Article:
    """Collected news article metadata."""

    title: str
    url: str
    published_at: datetime
    source: str
    section: Section
    description: str = ""
    view_count: int | None = None
    feed_rank: int | None = None


@dataclass(frozen=True, slots=True)
class PracticePoint:
    """Article-specific operational note generated from its body."""

    article_url: str
    text: str


@dataclass(frozen=True, slots=True)
class OfficialPressRelease:
    """A press release published on an official ministry or agency board."""

    agency: str
    title: str
    url: str
    published_on: date


@dataclass(frozen=True, slots=True)
class Briefing:
    """Selected newsletter articles grouped by section."""

    sections: dict[Section, tuple[Article, ...]]
