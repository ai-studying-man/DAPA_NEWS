"""Confirm whether an article belongs to the Korea-or-U.S. service scope."""

import re
from typing import Final

from dapa_morning_brief.business_rules import DEFENSE_COMPANY_KEYWORDS
from dapa_morning_brief.sources import (
    AGENCY_KEYWORDS,
    DOMESTIC_WEAPON_PROGRAM_KEYWORDS,
)

STRONG_KOREAN_SCOPE_KEYWORDS: Final[tuple[str, ...]] = (
    *AGENCY_KEYWORDS,
    *DOMESTIC_WEAPON_PROGRAM_KEYWORDS,
    *DEFENSE_COMPANY_KEYWORDS,
    "대한민국",
    "한국",
    "K-방산",
    "K방산",
    "한화 필리조선소",
    "이재명 대통령",
    "이 대통령",
    "李",
    "대통령실",
)
KOREAN_CONTEXT_KEYWORDS: Final[tuple[str, ...]] = (
    "우리 군",
    "국군",
    "국회",
    "국내",
    "국산",
)
KOREAN_POLICY_SCOPE_KEYWORDS: Final[tuple[str, ...]] = (
    "방위사업",
    "방위력개선",
    "국방획득",
    "국방조달",
    "방위사업법",
    "국방예산",
    "국방정책",
    "선행연구",
    "탐색개발",
    "국방첨단인증",
    "국방품질",
    "국방기술품질원",
    "국방규격",
    "방산혁신클러스터",
    "군용기 MRO",
    "함정 MRO",
)
KOREAN_OFFICIAL_SOURCE_KEYWORDS: Final[tuple[str, ...]] = (
    "국방부",
    "국방일보",
    "방위사업청",
    "방사청",
    "대한민국 정책브리핑",
    "정책브리핑",
    "국방과학연구소",
    "국방기술품질원",
)
KOREAN_LATIN_SOURCE_KEYWORDS: Final[tuple[str, ...]] = (
    "ytn",
    "kbs",
    "sbs",
    "mbc",
    "jtbc",
    "news1",
    "yna",
    "arirang",
    "korea herald",
    "korea times",
)
HANGUL_PATTERN: Final[re.Pattern[str]] = re.compile(r"[가-힣]")
FOREIGN_CONTEXT_MARKERS: Final[tuple[str, ...]] = (
    "브라질",
    "타이완",
    "대만",
    "중국",
    "중화인민공화국",
    "일본",
    "러시아",
    "북한",
    "베트남",
    "우크라이나",
    "폴란드",
    "루마니아",
    "이스라엘",
    "이란",
    "튀르키예",
    "国际在线",
    "vietnam.vn",
)
FOREIGN_PRIMARY_COUNTRIES: Final[tuple[str, ...]] = (
    "브라질",
    "타이완",
    "대만",
    "중국",
    "중화인민공화국",
    "일본",
    "러시아",
    "북한",
    "베트남",
    "우크라이나",
    "폴란드",
    "루마니아",
    "이스라엘",
    "이란",
    "튀르키예",
)
FOREIGN_PRIMARY_COUNTRY_PATTERN: Final[str] = "|".join(
    re.escape(country) for country in FOREIGN_PRIMARY_COUNTRIES
)
HEADLINE_PREFIX_PATTERN: Final[str] = r"^(?:\[[^\]]+\]\s*)*"
HEADLINE_SUFFIX_PATTERN: Final[str] = r"(?=$|[\s,:·\"“\u2018은는이가을를의와과에서만])"
DOMESTIC_GOVERNMENT_ACTORS: Final[tuple[str, ...]] = (
    "李",
    "국방부",
    "정부",
    "대통령실",
    "대통령",
    "국무총리",
    "국방장관",
    "합참의장",
    "육군참모총장",
    "해군참모총장",
    "공군참모총장",
    "육군",
    "해군",
    "공군",
    "해병대",
    "군",
)
KOREAN_DEFENSE_ACTORS: Final[tuple[str, ...]] = (
    "국방부",
    "국방장관",
    "합참의장",
    "육군참모총장",
    "해군참모총장",
    "공군참모총장",
    "육군",
    "해군",
    "공군",
    "해병대",
    "군",
)
CURRENT_DEFENSE_LEADERS: Final[tuple[str, ...]] = (
    "국방장관",
    "합참의장",
    "육군참모총장",
    "해군참모총장",
    "공군참모총장",
)
NON_CURRENT_MARKERS: Final[tuple[str, ...]] = (
    "출신",
    "전직",
    "후보",
    "후보자",
    "지명자",
)
DOMESTIC_GOVERNMENT_ACTOR_PATTERN: Final[str] = "|".join(DOMESTIC_GOVERNMENT_ACTORS)
KOREAN_DEFENSE_ACTOR_PATTERN: Final[str] = "|".join(KOREAN_DEFENSE_ACTORS)
CURRENT_DEFENSE_LEADER_PATTERN: Final[str] = "|".join(CURRENT_DEFENSE_LEADERS)
NON_CURRENT_MARKER_PATTERN: Final[str] = "|".join(NON_CURRENT_MARKERS)
US_DEFENSE_AUTHORITY_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:미국|미|美)\s*(?:국방부|국방장관|육군|해군|공군|해병대)|펜타곤",
    flags=re.IGNORECASE,
)
FOREIGN_PRIMARY_AUTHORITY_PATTERN: Final[re.Pattern[str]] = re.compile(
    "".join(
        (
            r"^(?:\[[^\]]+\]\s*)*",
            rf"(?:{FOREIGN_PRIMARY_COUNTRY_PATTERN})(?:의)?\s+",
            r"(?:정부|국방부|국방성|방위성|국방장관|대통령|총통|국가주석|군)",
            r"(?=$|[\s,:·은는이가])",
        ),
    ),
    flags=re.IGNORECASE,
)
DOMESTIC_GOVERNMENT_HEADLINE_PATTERN: Final[re.Pattern[str]] = re.compile(
    rf"{HEADLINE_PREFIX_PATTERN}(?:{DOMESTIC_GOVERNMENT_ACTOR_PATTERN}){HEADLINE_SUFFIX_PATTERN}",
)
KOREAN_DEFENSE_HEADLINE_PATTERN: Final[re.Pattern[str]] = re.compile(
    rf"{HEADLINE_PREFIX_PATTERN}(?:{KOREAN_DEFENSE_ACTOR_PATTERN}){HEADLINE_SUFFIX_PATTERN}",
)
NON_CURRENT_DEFENSE_LEADER_PATTERN: Final[re.Pattern[str]] = re.compile(
    rf"{HEADLINE_PREFIX_PATTERN}(?:{CURRENT_DEFENSE_LEADER_PATTERN})\s*(?:{NON_CURRENT_MARKER_PATTERN})",
)


def has_foreign_primary_authority(title: str) -> bool:
    """Return whether a non-Korean, non-U.S. authority leads the headline."""
    return FOREIGN_PRIMARY_AUTHORITY_PATTERN.search(title.strip()) is not None


def is_us_defense_institution_news(title: str) -> bool:
    """Return whether the headline covers a U.S. defense institution directly."""
    return not has_foreign_primary_authority(title) and bool(
        US_DEFENSE_AUTHORITY_PATTERN.search(title),
    )


def is_korean_defense_ministry_news(title: str, source: str) -> bool:
    """Return whether metadata identifies the Korean defense ministry or military."""
    if _contains_any(source, KOREAN_OFFICIAL_SOURCE_KEYWORDS):
        return True
    if has_foreign_primary_authority(title):
        return False
    if NON_CURRENT_DEFENSE_LEADER_PATTERN.search(title.strip()):
        return False
    if not _source_supports_korean_context(source):
        return False
    if not KOREAN_DEFENSE_HEADLINE_PATTERN.search(title.strip()):
        return False
    return not _contains_any(f"{title} {source}", FOREIGN_CONTEXT_MARKERS)


def article_scope_is_allowed(text: str, title: str, source: str) -> bool:
    """Allow only confirmed Korean or U.S. defense coverage."""
    if _contains_any(text, STRONG_KOREAN_SCOPE_KEYWORDS):
        return True
    if has_foreign_primary_authority(title):
        return False
    if is_us_defense_institution_news(title):
        return True
    if not _source_supports_korean_context(source):
        return False
    return (
        _contains_any(text, KOREAN_CONTEXT_KEYWORDS)
        or _contains_any(text, KOREAN_POLICY_SCOPE_KEYWORDS)
        or bool(DOMESTIC_GOVERNMENT_HEADLINE_PATTERN.search(title.strip()))
        or is_korean_defense_ministry_news(title, source)
    )


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    normalized = text.casefold()
    return any(needle.casefold() in normalized for needle in needles)


def _source_supports_korean_context(source: str) -> bool:
    normalized = source.strip().casefold()
    return (
        not normalized
        or HANGUL_PATTERN.search(normalized) is not None
        or _contains_any(normalized, KOREAN_LATIN_SOURCE_KEYWORDS)
    )
