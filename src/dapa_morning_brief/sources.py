"""Source definitions and relevance keywords for the morning brief."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from dapa_morning_brief.models import Section

USER_AGENT: Final[str] = (
    "DAPA-Morning-Brief/0.1 "
    "(public RSS newsletter automation; contact: repository owner)"
)

AGENCY_KEYWORDS: Final[tuple[str, ...]] = ("방위사업청", "방사청")
AGENCY_QUERY: Final[str] = '"방위사업청" OR "방사청"'

GOVERNMENT_ACTOR_KEYWORDS: Final[tuple[str, ...]] = (
    "이재명 대통령",
    "대통령",
    "대통령실",
    "정부",
    "국무총리",
    "국방부 장관",
    "국방장관",
    "합참의장",
    "육군참모총장",
    "해군참모총장",
    "공군참모총장",
)

POLICY_KEYWORDS: Final[tuple[str, ...]] = (
    "방위사업청",
    "방사청",
    "방위사업",
    "방위력개선",
    "국방획득",
    "국방조달",
    "방위사업법",
    "국방예산",
    "국방정책",
    "선행연구",
    "탐색개발",
)

WEAPON_SYSTEM_KEYWORDS: Final[tuple[str, ...]] = (
    "무기체계",
    "전력화",
    "체계개발",
    "시험평가",
    "야전운용시험",
    "양산사업",
    "후속양산",
    "최초양산",
    "ROC",
    "CDR",
    "PDR",
    "KF-21",
    "KDDX",
    "L-SAM",
    "M-SAM",
    "천궁",
    "K2",
    "K9",
    "전차",
    "전투기",
    "함정",
    "잠수함",
    "미사일",
    "드론",
    "무인기",
)

GENERIC_WEAPON_KEYWORDS: Final[tuple[str, ...]] = (
    "드론",
    "무인기",
    "미사일",
    "전차",
    "전투기",
    "함정",
    "잠수함",
    "AI",
    "우주",
)

DEFENSE_TECH_KEYWORDS: Final[tuple[str, ...]] = (
    "AI",
    "인공지능",
    "무인화",
    "무인체계",
    "유무인복합",
)

DEFENSE_ANCHOR_KEYWORDS: Final[tuple[str, ...]] = (
    *POLICY_KEYWORDS,
    "국방부",
    "군",
    "육군",
    "해군",
    "공군",
    "해병대",
    "ADD",
    "국방과학연구소",
)

DEFENSE_BUSINESS_KEYWORDS: Final[tuple[str, ...]] = (
    "방산",
    "K방산",
    "K-방산",
    "방산수출",
    "방산기업",
    "방위산업",
    "방산계약",
    "절충교역",
    "한화에어로스페이스",
    "한화시스템",
    "한화오션",
    "LIG넥스원",
    "현대로템",
    "한국항공우주",
    "KAI",
    "풍산",
    "대한항공",
)

DEFENSE_CONTEXT_KEYWORDS: Final[tuple[str, ...]] = (
    *POLICY_KEYWORDS,
    *WEAPON_SYSTEM_KEYWORDS,
    *DEFENSE_BUSINESS_KEYWORDS,
    "국방부",
    "군",
    "육군",
    "해군",
    "공군",
    "ADD",
    "국방과학연구소",
)

EXCLUDE_KEYWORDS: Final[tuple[str, ...]] = (
    "연예",
    "스포츠",
    "야구",
    "축구",
    "농구",
    "게임",
    "드라마",
    "영화",
    "음원",
    "맛집",
    "여행",
    "부동산",
    "코인",
    "가상자산",
    "주가 전망",
    "증시",
    "고문 영입",
    "영입",
    "전 대통령",
    "전대통령",
    "윤 전 대통령",
    "평양 무인기",
    "사망",
    "지병",
    "사고",
)

FOREIGN_CONTEXT_KEYWORDS: Final[tuple[str, ...]] = (
    "러시아",
    "러,",
    "우크라",
    "프랑스",
    "미국",
    "중국",
    "일본",
    "북한",
)

KOREA_ANCHOR_KEYWORDS: Final[tuple[str, ...]] = (
    "한국",
    "대한민국",
    "우리 군",
    "軍",
    "국방부",
    "방위사업청",
    "방사청",
    "국회",
    "정부",
    "육군",
    "해군",
    "공군",
    "해병대",
    "K-방산",
    "K방산",
)

SECTION_QUERIES: Final[dict[Section, str]] = {
    Section.GOVERNMENT: (
        '"정부" 방산 OR "대통령" 방산 OR "대통령실" 국방 '
        'OR "국무총리" 방산 OR "국방부 장관" 방산 OR "국방장관" 방산 '
        'OR "합참의장" 무기체계 OR "육군참모총장" 전력화 '
        'OR "해군참모총장" 전력화 OR "공군참모총장" 전력화'
    ),
    Section.POLICY: (
        '"방위사업청" OR "방사청" OR "방위사업" OR "방위력개선" '
        'OR "국방획득" OR "국방조달" OR "방위사업법" OR "국방예산" '
        'OR "국방정책" OR "선행연구" OR "탐색개발" '
        'OR "국방부" "AI" OR "국방부" "무인화" '
        'OR "방산" "AI" OR "방산" "무인화" '
        'OR "방위사업" "AI" OR "방위사업" "무인화"'
    ),
    Section.WEAPON_SYSTEM: (
        '"무기체계" OR "전력화" OR "체계개발" OR "양산사업" '
        'OR "후속양산" OR "최초양산" OR "시험평가" OR "야전운용시험" '
        'OR "ROC" OR "CDR" OR "PDR" OR "KF-21" OR "L-SAM" '
        'OR "K2 전차" OR "K9" OR "천궁" OR "드론" OR "무인기"'
    ),
    Section.EXPORT_BUSINESS: (
        '"방산수출" OR "K방산" OR "K-방산" OR "방산기업" '
        'OR "방위산업" OR "방산계약" OR "절충교역" '
        'OR "한화에어로스페이스" OR "한화시스템" OR "LIG넥스원" '
        'OR "현대로템" OR "한국항공우주" OR "KAI" OR "풍산"'
    ),
}

BROAD_FALLBACK_QUERY: Final[str] = (
    '"방위사업청" OR "방사청" OR "방위사업" OR "무기체계" '
    'OR "방산수출" OR "K방산" OR "K-방산" '
    'OR "국방부" "AI" OR "방산" "무인화"'
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

RELEVANT_KEYWORDS: Final[tuple[str, ...]] = DEFENSE_CONTEXT_KEYWORDS


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
