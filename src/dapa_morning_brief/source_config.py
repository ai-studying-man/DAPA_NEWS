"""RSS endpoints and Google News query configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from dapa_morning_brief.models import Section

USER_AGENT: Final[str] = (
    "DAPA-Morning-Brief/0.1 "
    "(public RSS newsletter automation; contact: repository owner)"
)
AGENCY_QUERY: Final[str] = '"방위사업청" OR "방사청"'


def _query(*parts: str) -> str:
    return " ".join(parts)


SECTION_QUERIES: Final[dict[Section, tuple[str, ...]]] = {
    Section.GOVERNMENT: (
        '"국방부"',
        _query(
            '"대통령" "국무회의" OR "대통령" "업무보고"',
            'OR "대통령실" "국정과제" OR "대통령실" "업무보고"',
            'OR "정부" "국정과제" OR "정부" "국정성과" OR "정부" "업무보고"',
        ),
        _query(
            '"정부" 방산 OR "대통령" 방산 OR "대통령실" 국방',
            'OR "국무총리" 방산 OR "국방부 장관" 방산 OR "국방장관" 방산',
            'OR "합참의장" 무기체계 OR "육군참모총장" 전력화',
            'OR "해군참모총장" 전력화 OR "공군참모총장" 전력화',
        ),
    ),
    Section.POLICY: (
        _query(
            '"방위사업청" OR "방사청" OR "방위사업" OR "방위력개선"',
            'OR "국방획득" OR "국방조달" OR "방위사업법" OR "국방예산"',
            'OR "국방정책" OR "선행연구" OR "탐색개발"',
            'OR "국방부" "AI" OR "국방부" "무인화"',
            'OR "방산" "AI" OR "방산" "무인화"',
            'OR "방위사업" "AI" OR "방위사업" "무인화"',
        ),
        _query(
            '"국방첨단인증" OR "국방품질" OR "국방기술품질원" OR "국방규격"',
            'OR "방산혁신클러스터" OR "군용기 MRO" OR "함정 MRO"',
        ),
    ),
    Section.WEAPON_SYSTEM: (
        _query(
            '"무기체계" OR "전력화" OR "체계개발" OR "양산사업"',
            'OR "후속양산" OR "최초양산" OR "시험평가" OR "야전운용시험"',
            'OR "ROC" OR "CDR" OR "PDR" OR "KF-21" OR "L-SAM"',
            'OR "K2 전차" OR "K9 자주포" OR "천궁" OR "드론" OR "무인기"',
        ),
        _query(
            '"K2C1" OR "F-15K" OR "KF-16" OR "링크-22" OR "Link-22"',
            'OR "자폭드론" OR "무인잠수정" OR "특수선" OR "한국 호위함"',
        ),
    ),
    Section.EXPORT_BUSINESS: (
        _query(
            '"방산수출" OR "K방산" OR "K-방산" OR "방산기업"',
            'OR "방위산업" OR "방산계약" OR "절충교역"',
            'OR "한화에어로스페이스" OR "한화시스템" OR "LIG넥스원"',
            'OR "현대로템" OR "한국항공우주" OR "KAI" OR "풍산"',
        ),
        _query(
            '"K조선" OR "K-조선" OR "함정 수출" OR "방산 공급망"',
            'OR "방산 스타트업" OR "NATO 품질인증" OR "나토 품질인증"',
        ),
    ),
}

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
        name="정책브리핑 방위사업청",
        url="https://www.korea.kr/rss/dept_dapa.xml",
        default_section=Section.POLICY,
    ),
    RssSource(
        name="정책브리핑 국방부",
        url="https://www.korea.kr/rss/dept_mnd.xml",
        default_section=Section.POLICY,
    ),
    RssSource(
        name="정책브리핑 보도자료",
        url="https://www.korea.kr/rss/pressrelease.xml",
        default_section=None,
    ),
    RssSource(
        name="국방일보 방위사업",
        url="http://kookbang.dema.mil.kr/dema_xml/dema0010020000.xml",
        default_section=None,
    ),
)
