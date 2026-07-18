"""Defense-industry company, event, and export classification rules."""

import re
from typing import Final

from dapa_morning_brief.sources import (
    DEFENSE_ANCHOR_KEYWORDS,
    GENERIC_WEAPON_KEYWORDS,
    WEAPON_SYSTEM_KEYWORDS,
)

DEFENSE_INDUSTRY_KEYWORDS: Final[tuple[str, ...]] = (
    "방산",
    "K방산",
    "K-방산",
    "방산수출",
    "방산기업",
    "방위산업",
    "방산계약",
    "절충교역",
    "함정 수출",
    "특수선",
    "NATO 품질인증",
    "나토 품질인증",
)

DEFENSE_COMPANY_KEYWORDS: Final[tuple[str, ...]] = (
    "한화에어로스페이스",
    "한화시스템",
    "한화오션",
    "LIG넥스원",
    "현대로템",
    "한국항공우주",
    "KAI",
    "풍산",
    "대한항공",
    "HD현대중공업",
    "HD현대",
    "K조선",
    "K-조선",
)

DEFENSE_BUSINESS_KEYWORDS: Final[tuple[str, ...]] = (
    *DEFENSE_INDUSTRY_KEYWORDS,
    *DEFENSE_COMPANY_KEYWORDS,
)

DIRECT_EXPORT_KEYWORDS: Final[tuple[str, ...]] = (
    "수출",
    "해외",
    "글로벌",
)

EXPORT_TRANSACTION_KEYWORDS: Final[tuple[str, ...]] = (
    "수주",
    "최종 인도",
    "인도 완료",
    "최종 납품",
    "납품 완료",
    "해외 납품",
)

FOREIGN_MARKET_KEYWORDS: Final[tuple[str, ...]] = (
    "인도네시아",
    "폴란드",
    "루마니아",
    "사우디",
    "아랍에미리트",
    "UAE",
    "이라크",
    "중동",
    "유럽",
    "미국",
    "美",
    "캐나다",
    "호주",
    "필리핀",
    "태국",
    "말레이시아",
    "페루",
)

EXPORT_BUSINESS_TREND_KEYWORDS: Final[tuple[str, ...]] = (
    "공급망",
    "스타트업",
    "파트너십",
    "NATO 품질인증",
    "나토 품질인증",
)

DEFENSE_EXPORT_PROGRAM_KEYWORDS: Final[tuple[str, ...]] = (
    "K2",
    "K9 자주포",
    "KF-21",
    "KDDX",
    "L-SAM",
    "M-SAM",
    "천궁",
    "T-50",
    "T-50i",
)

SPECIFIC_WEAPON_KEYWORDS: Final[tuple[str, ...]] = tuple(
    keyword
    for keyword in WEAPON_SYSTEM_KEYWORDS
    if keyword not in GENERIC_WEAPON_KEYWORDS
)
STANDALONE_MILITARY_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?<![0-9a-z가-힣])군(?=$|[\s,:·은이가])",
)


def is_defense_export_news(text: str) -> bool:
    """Return whether text describes a defense export or industry trend."""
    industry_event = _contains_any(text, DEFENSE_INDUSTRY_KEYWORDS) and (
        _has_export_direction(text)
        or _contains_any(text, EXPORT_BUSINESS_TREND_KEYWORDS)
    )
    company_export = (
        _contains_any(text, DEFENSE_COMPANY_KEYWORDS)
        and _has_export_direction(text)
        and (
            _contains_any(text, DEFENSE_INDUSTRY_KEYWORDS)
            or _contains_any(text, SPECIFIC_WEAPON_KEYWORDS)
        )
    )
    program_export = _contains_any(
        text,
        DEFENSE_EXPORT_PROGRAM_KEYWORDS,
    ) and _has_export_direction(text)
    return industry_event or company_export or program_export


def is_defense_business_news(text: str) -> bool:
    """Return whether company coverage has an explicit defense context."""
    if _contains_any(text, DEFENSE_INDUSTRY_KEYWORDS):
        return True
    return _contains_any(text, DEFENSE_COMPANY_KEYWORDS) and (
        contains_defense_anchor(text) or _contains_any(text, SPECIFIC_WEAPON_KEYWORDS)
    )


def contains_defense_anchor(text: str) -> bool:
    """Return whether text contains an explicit military or acquisition anchor."""
    return _contains_any(text, DEFENSE_ANCHOR_KEYWORDS) or bool(
        STANDALONE_MILITARY_PATTERN.search(text),
    )


def _has_export_direction(text: str) -> bool:
    return _contains_any(text, DIRECT_EXPORT_KEYWORDS) or (
        _contains_any(text, EXPORT_TRANSACTION_KEYWORDS)
        and _contains_any(text, FOREIGN_MARKET_KEYWORDS)
    )


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle.casefold() in text for needle in needles)
