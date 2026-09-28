"""Headline evidence for acquisition, weapons, and excluded topics."""

from __future__ import annotations

import re
from typing import Final

from dapa_morning_brief.article_scope import (
    KOREAN_OFFICIAL_SOURCE_KEYWORDS,
)
from dapa_morning_brief.business_rules import (
    DEFENSE_INDUSTRY_KEYWORDS,
    contains_defense_anchor,
    is_defense_business_headline,
    is_defense_business_news,
)
from dapa_morning_brief.entity_catalog import contains_any as _contains_any
from dapa_morning_brief.government_rules import (
    CURRENT_DEFENSE_LEADER_KEYWORDS,
    current_government_actor,
)
from dapa_morning_brief.sources import (
    AGENCY_KEYWORDS,
    DEFENSE_TECH_KEYWORDS,
    DOMESTIC_WEAPON_PROGRAM_KEYWORDS,
    GENERIC_WEAPON_KEYWORDS,
    KOREA_ANCHOR_KEYWORDS,
    WEAPON_SYSTEM_KEYWORDS,
)
from dapa_morning_brief.weapon_catalog import matching_weapons


def is_defense_tech_policy_news(text: str) -> bool:
    """Require a defense anchor for generic technology-policy evidence."""
    if not _contains_defense_tech_keyword(text):
        return False
    return contains_defense_anchor(text)


def _contains_defense_tech_keyword(text: str) -> bool:
    if re.search(r"(?<![a-z0-9])ai(?![a-z0-9])", text):
        return True
    return _contains_any(
        text,
        tuple(
            keyword for keyword in DEFENSE_TECH_KEYWORDS if keyword.casefold() != "ai"
        ),
    )


def is_weapon_system_news(text: str, *, source: str = "") -> bool:
    """Resolve weapon aliases only with their required military context."""
    if matching_weapons(text):
        return True
    if not _contains_any(text, WEAPON_SYSTEM_KEYWORDS):
        return False
    if _contains_any(text, DOMESTIC_WEAPON_PROGRAM_KEYWORDS):
        return True
    specific_weapon_keywords = tuple(
        keyword
        for keyword in WEAPON_SYSTEM_KEYWORDS
        if keyword not in GENERIC_WEAPON_KEYWORDS
    )
    if _contains_any(text, specific_weapon_keywords) and (
        _contains_any(text, KOREA_ANCHOR_KEYWORDS)
        or is_defense_business_news(text)
        or _contains_any(source, KOREAN_OFFICIAL_SOURCE_KEYWORDS)
    ):
        return True
    if _contains_any(text, GENERIC_WEAPON_KEYWORDS):
        return (
            contains_defense_anchor(text)
            or _contains_any(text, DEFENSE_INDUSTRY_KEYWORDS)
            or _contains_any(source, KOREAN_OFFICIAL_SOURCE_KEYWORDS)
        )
    return False


ACQUISITION_POLICY_TERMS: Final[tuple[str, ...]] = (
    "소요결정",
    "획득제도",
    "국방조달",
    "방위사업법",
    "부품국산화",
    "감항인증",
    "후속군수지원",
    "국방품질",
    "국방규격",
    "기술교범",
    "S1000D",
    "표준화",
    "국제표준",
    "규제개선",
    "규제 개선",
    "방산물자 지정",
    "방산업체 지정",
    "독과점",
    "카르텔",
)
ACQUISITION_FACT_TERMS: Final[tuple[str, ...]] = (
    "계약 체결",
    "계약체결",
    "양산 계약",
    "양산계약",
    "공급 계약",
    "공급계약",
    "납품 완료",
    "인도 완료",
    "시험평가",
    "체계개발",
    "성능개량",
    "부품국산화",
    "생산능력",
    "생산 능력",
    "생산시설",
    "생산 시설",
    "획득제도",
    "소요결정",
)


def has_acquisition_policy_topic(text: str) -> bool:
    """Require acquisition subject matter plus a defense or weapon anchor."""
    return _contains_any(text, ACQUISITION_POLICY_TERMS) and (
        contains_defense_anchor(text) or bool(matching_weapons(text))
    )


def has_acquisition_fact(text: str) -> bool:
    """Detect concrete acquisition facts that can justify an exclusion exception."""
    return _contains_any(text, ACQUISITION_FACT_TERMS) and (
        bool(matching_weapons(text))
        or _contains_any(text, ("무기체계", "국방획득", "국방조달", "유도무기", "군용"))
        or has_acquisition_policy_topic(text)
    )


def is_defense_leadership_appointment(title: str) -> bool:
    """Recognize presidential appointments to current defense leadership."""
    return (
        current_government_actor(title) in {"대통령", "대통령실"}
        and _contains_any(title, ("임명", "지명"))
        and _contains_any(title, CURRENT_DEFENSE_LEADER_KEYWORDS)
    )


def is_weapon_development_title(title: str, *, source: str) -> bool:
    """Distinguish weapon lifecycle actions from general technology mentions."""
    return is_weapon_system_news(title.casefold(), source=source) and _contains_any(
        title,
        (
            "국내개발",
            "국내 개발",
            "체계개발",
            "개발 착수",
            "초도양산",
            "전력화 완료",
            "시험평가 완료",
            "무인화",
            "성능개량",
            "시험비행",
            "진수",
        ),
    )


def is_civilian_site_housing(title: str) -> bool:
    """Separate civilian housing redevelopment from military accommodation."""
    site = _contains_any(title, ("부지", "반환기지", "이전 터"))
    housing = _contains_any(
        title, ("주택", "아파트", "재개발", "택지", "분양")
    ) or bool(
        re.search(r"\d[\d,만천백]*\s*호(?=$|[\s,·…])", title),
    )
    military_facility = _contains_any(
        title,
        ("군 숙소", "군숙소", "병영시설", "군 관사", "군관사", "군인 아파트"),
    )
    return site and housing and not military_facility


def is_public_procurement_headline(title: str) -> bool:
    """Recognize procurement-rule subjects independently of examples."""
    return _contains_any(
        title,
        ("공공사업", "공공 소프트웨어", "공공SW", "대참제", "입찰제도", "조달제도"),
    )


def has_unrelated_headline(title: str, description: str) -> bool:
    """Reject non-newsletter subjects even with defense background snippets."""
    financing = _contains_any(
        title,
        (
            "증권신고서",
            "기업공개",
            "IPO",
            "공모주",
            "상장 절차",
            "목표가",
            "목표주가",
            "주가",
            "주식",
        ),
    )
    profile = title.strip().casefold().startswith(("[who is", "[인물탐구", "[인물소개"))
    stock_movement = re.search(
        r"방산\s*주|%\s*[↑↓]|%대?\s*(?:강세|약세)|종목|급등|급락|상한가|하한가",
        title,
    ) or re.search(r"\d[\d,.]*만?원대?\s*(?:상승|하락)", title)
    recruiting = _contains_any(title, ("채용", "취업"))
    entertainment = _contains_any(
        title, ("Game &", "TFT", "e스포츠", "e-스포츠", "페스티벌", "축제")
    )
    relocation_campaign = _contains_any(title, ("국방연구원", "공공기관")) and (
        _contains_any(title, ("유치", "이전 부지"))
    )
    civilian_local = _contains_any(title, ("분양", "공약사업")) and not _contains_any(
        title,
        ("국방", "방산", "병영", "군 숙소", "군 관사", "군인 아파트"),
    )
    if (
        financing
        or profile
        or stock_movement
        or recruiting
        or civilian_local
        or entertainment
        or relocation_campaign
    ) and not has_acquisition_fact(title):
        return True
    incidental_agency = _contains_any(
        description, (*AGENCY_KEYWORDS, "국방부")
    ) and not _contains_any(
        title,
        (*AGENCY_KEYWORDS, "국방부"),
    )
    headline_context = (
        _contains_any(title, ("국방", "방산", "방위", "획득", "군용", "장병", "병영"))
        or _contains_any(title, WEAPON_SYSTEM_KEYWORDS)
        or is_defense_business_news(title.casefold())
        or is_defense_business_headline(title)
        or is_public_procurement_headline(title)
    )
    return incidental_agency and not headline_context
