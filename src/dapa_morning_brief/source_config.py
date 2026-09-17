"""RSS endpoints and Google News query configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from dapa_morning_brief.entity_catalog import COMPANY_ALIASES
from dapa_morning_brief.models import Section
from dapa_morning_brief.weapon_catalog import WEAPON_CATALOG

USER_AGENT: Final[str] = (
    "DAPA-Morning-Brief/0.1 "
    "(public RSS newsletter automation; contact: repository owner)"
)
AGENCY_QUERY: Final[str] = '"방위사업청" OR "방사청"'


def _query(*parts: str) -> str:
    return " ".join(parts)


def _or_groups(terms: tuple[str, ...]) -> tuple[str, ...]:
    """Keep Google queries short; each term remains a literal phrase."""
    return tuple(
        " OR ".join(f'"{term}"' for term in terms[start : start + 4])
        for start in range(0, len(terms), 4)
    )


ACQUISITION_SEARCH_TERMS: Final[tuple[str, ...]] = (
    "방위사업청",
    "방사청",
    "국방획득",
    "국방조달",
    "방위력개선",
    "방위사업법",
    "국방예산",
    "국방정책",
    "소요결정",
    "선행연구",
    "탐색개발",
    "국방첨단인증",
    "국방품질",
    "국방기술품질원",
    "국방규격",
    "방산혁신클러스터",
    "군용기 MRO",
    "함정 MRO",
    "부품국산화",
    "감항인증",
    "후속군수지원",
)
WEAPON_SEARCH_TERMS: Final[tuple[str, ...]] = (
    "무기체계",
    "전력화",
    "체계개발",
    "초도양산",
    "후속양산",
    "시험평가",
    "야전운용시험",
    "실전 배치",
    "작전 배치",
    "군 인도",
    "성능개량",
    "KDDX",
    "L-SAM",
    "M-SAM",
    "F-15K",
    "KF-16",
    "K2C1",
    "한국 링크-22",
    "한국 호위함",
    *(
        f"{alias} {entry.context[0]}" if entry.context else alias
        for entry in WEAPON_CATALOG
        for alias in entry.aliases
    ),
)
COMPANY_SEARCH_TERMS: Final[tuple[str, ...]] = (
    *(alias for group in COMPANY_ALIASES for alias in group),
    "LIG 방산",
    "풍산 방산",
    "HD현대중공업 함정",
)
SECTION_QUERIES: Final[dict[Section, tuple[str, ...]]] = {
    Section.GOVERNMENT: (
        '"국방부"',
        '"대통령" "국무회의" OR "대통령" "업무보고"',
        '"대통령실" "국정과제" OR "정부" "국정성과"',
        '"정부" 방산 OR "대통령" "방산" OR "대통령실" "국방"',
        '"국무총리" "방산" OR "국방부 장관" "방산"',
        '"합참의장" "무기체계" OR "육군참모총장" "전력화"',
        '"해군참모총장" "전력화" OR "공군참모총장" "전력화"',
    ),
    Section.POLICY: (
        *_or_groups(ACQUISITION_SEARCH_TERMS),
        '"국방" "AI" OR "방산" "무인화" OR "군용" "인공지능"',
    ),
    Section.WEAPON_SYSTEM: (
        *_or_groups(WEAPON_SEARCH_TERMS),
        '("국방" OR "군용" OR "방산") ("드론" OR "무인기" OR "무인항공기")',
        '("한국" OR "국군") ("레이더" OR "전자전" OR "소나" OR "정찰위성")',
        '("국방" OR "군용") ("탄약" OR "통신장비" OR "화생방" OR "대드론")',
    ),
    Section.EXPORT_BUSINESS: (
        *_or_groups(COMPANY_SEARCH_TERMS),
        *_or_groups(
            (
                "K조선",
                "방산수출",
                "K방산",
                "K-방산",
                "방위산업",
                "방산 공급망",
                "방산 스타트업",
                "NATO 품질인증",
                "나토 품질인증",
            )
        ),
    ),
}
# Naver accepts separate keyword searches, not Google's OR/when operators.
NAVER_SEARCH_QUERIES: Final[tuple[str, ...]] = tuple(
    dict.fromkeys(
        (
            "국방부",
            "대통령 국방",
            *ACQUISITION_SEARCH_TERMS,
            *WEAPON_SEARCH_TERMS,
            *COMPANY_SEARCH_TERMS,
            "국방 드론",
            "군용 무인항공기",
            "방산수출",
            "한국 레이더",
            "군용 통신장비",
        )
    )
)

BROAD_FALLBACK_QUERY: Final[str] = _query(
    '"방위사업청" OR "방사청" OR "방위사업" OR "무기체계"',
    'OR "방산수출" OR "K방산" OR "K-방산"',
    'OR "국방부" "AI" OR "방산" "무인화"',
)
SINGLE_FALLBACK_KEYWORDS: Final[tuple[str, ...]] = (
    "방위사업청",
    "방사청",
    "방위사업",
    "무기체계",
    "전력화",
    "시험평가",
    "방산수출",
    "K방산",
)


@dataclass(frozen=True, slots=True)
class RssSource:
    """RSS source metadata."""

    name: str
    url: str
    default_section: Section | None


RSS_SOURCES: Final[tuple[RssSource, ...]] = (
    RssSource(
        name="국방일보 방위사업",
        url="http://kookbang.dema.mil.kr/dema_xml/dema0010020000.xml",
        default_section=None,
    ),
)
