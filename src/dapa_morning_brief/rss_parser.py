"""Parse and classify RSS article metadata."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, time, timedelta, timezone
from typing import Final

from dapa_morning_brief.article_scope import (
    KOREAN_OFFICIAL_SOURCE_KEYWORDS,
    article_scope_is_allowed,
    has_foreign_primary_authority,
    is_korean_defense_ministry_news,
    is_us_defense_institution_news,
)
from dapa_morning_brief.business_rules import (
    DEFENSE_INDUSTRY_KEYWORDS,
    contains_defense_anchor,
    is_company_social_event,
    is_defense_business_news,
    is_defense_export_news,
    is_foreign_procurement_news,
)
from dapa_morning_brief.entity_catalog import contains_any as _contains_any
from dapa_morning_brief.government_rules import (
    CURRENT_DEFENSE_LEADER_KEYWORDS,
    CURRENT_GOVERNMENT_LEADER_KEYWORDS,
    CURRENT_GOVERNMENT_POLICY_KEYWORDS,
    GENERAL_GOVERNMENT_POLICY_KEYWORDS,
    current_government_actor,
)
from dapa_morning_brief.models import Article, Section
from dapa_morning_brief.rss_metadata import (
    _clean_description,
    _clean_title,
    _parse_date,
    _source_from_item,
    _text,
    _view_count_from_item,
)
from dapa_morning_brief.sources import (
    AGENCY_KEYWORDS,
    DEFENSE_TECH_KEYWORDS,
    DOMESTIC_WEAPON_PROGRAM_KEYWORDS,
    EXCLUDE_KEYWORDS,
    GENERIC_WEAPON_KEYWORDS,
    KOREA_ANCHOR_KEYWORDS,
    POLICY_KEYWORDS,
    SOFT_EXCLUDE_KEYWORDS,
    UNTRUSTED_SOURCE_KEYWORDS,
    UNTRUSTED_TITLE_PREFIXES,
    WEAPON_SYSTEM_KEYWORDS,
)
from dapa_morning_brief.weapon_catalog import matching_weapons

KST = timezone(timedelta(hours=9))
SEND_WINDOW_START = time(hour=6, minute=30, tzinfo=KST)
MAX_RSS_CHARACTERS = 5_000_000


def parse_rss_items(
    xml_text: str,
    *,
    source_name: str,
    default_section: Section | None,
    days: int,
    now: datetime,
) -> list[Article]:
    """Parse RSS XML into article metadata."""
    if len(xml_text) > MAX_RSS_CHARACTERS:
        msg = "RSS response exceeds the parser size limit"
        raise ValueError(msg)

    # ElementTree does not resolve external entities; input size is bounded above.
    root = ET.fromstring(xml_text)  # noqa: S314
    cutoff = _freshness_cutoff(now, days=days)
    articles: list[Article] = []

    for feed_rank, item in enumerate(root.findall(".//item")):
        title = _text(item, "title")
        link = _text(item, "link")
        description = _clean_description(_text(item, "description"))
        source = _source_from_item(item) or source_name
        published_at = _parse_date(_text(item, "pubDate"))
        if not title or not link or published_at is None or published_at < cutoff:
            continue
        if not is_relevant_article(title, description, source):
            continue
        metadata_text = f"{title} {description}".casefold()
        if default_section is Section.GOVERNMENT and not _is_current_government_news(
            metadata_text,
            title,
            source,
        ):
            continue
        section = default_section or classify_title(
            title,
            description=description,
            source=source,
        )
        articles.append(
            Article(
                title=_clean_title(title, source=source),
                url=link,
                published_at=published_at,
                source=source,
                section=section,
                description=description,
                view_count=_view_count_from_item(item),
                feed_rank=feed_rank,
            ),
        )

    return articles


def classify_title(
    title: str,
    *,
    description: str = "",
    source: str = "",
) -> Section:
    """Classify an article title into the closest newsletter section."""
    text = f"{title} {description}".casefold()
    if is_company_social_event(text):
        section = Section.EXPORT_BUSINESS
    elif _has_acquisition_policy_topic(title) or _is_public_procurement_headline(title):
        section = Section.POLICY
    elif _is_current_government_news(text, title, source):
        section = Section.GOVERNMENT
    elif is_defense_export_news(text) or is_foreign_procurement_news(title, text):
        section = Section.EXPORT_BUSINESS
    elif _is_weapon_development_title(title, source=source):
        section = Section.WEAPON_SYSTEM
    elif _is_defense_tech_policy_news(text):
        section = Section.POLICY
    elif _is_weapon_system_news(text, source=source):
        section = Section.WEAPON_SYSTEM
    elif _contains_any(text, POLICY_KEYWORDS):
        section = Section.POLICY
    elif is_defense_business_news(text):
        section = Section.EXPORT_BUSINESS
    else:
        section = Section.POLICY
    return section


def is_relevant_title(title: str) -> bool:
    """Return whether a title is relevant enough for DAPA morning brief."""
    return is_relevant_article(title, "", "")


def is_relevant_article(title: str, description: str, source: str) -> bool:
    """Return whether available RSS metadata is relevant to the brief."""
    text = f"{title} {description}".casefold()
    normalized_title = title.strip().casefold()
    if (
        normalized_title.startswith(UNTRUSTED_TITLE_PREFIXES)
        or _contains_any(
            source.casefold(),
            UNTRUSTED_SOURCE_KEYWORDS,
        )
        or _has_unrelated_headline(title, description)
    ):
        return False
    if (
        _contains_any(text, SOFT_EXCLUDE_KEYWORDS) or _is_civilian_site_housing(title)
    ) and not (
        _has_acquisition_fact(text) or _is_defense_leadership_appointment(title)
    ):
        return False
    if _contains_any(text, AGENCY_KEYWORDS) or is_company_social_event(text):
        return True
    if _contains_any(text, EXCLUDE_KEYWORDS):
        return False
    if not article_scope_is_allowed(text, title, source):
        return False
    defense_export = is_defense_export_news(text) or is_foreign_procurement_news(
        title, text
    )
    return (
        _is_current_government_news(text, title, source)
        or _is_defense_tech_policy_news(text)
        or defense_export
        or _contains_any(text, POLICY_KEYWORDS)
        or _is_weapon_system_news(text, source=source)
        or is_defense_business_news(text)
    )


def _is_current_government_news(text: str, title: str, source: str) -> bool:
    if has_foreign_primary_authority(title):
        return False
    if not article_scope_is_allowed(text, title, source):
        return False
    alliance_news = is_us_defense_institution_news(title) and _contains_any(
        title,
        ("한미동맹", "주한미군", "한미 연합"),
    )
    if alliance_news or _is_defense_leadership_appointment(title):
        return True
    official_personnel_news = _contains_any(
        source, KOREAN_OFFICIAL_SOURCE_KEYWORDS
    ) and _contains_any(
        title,
        ("장병", "복무여건", "병영", "국방정책", "국방예산", "서울안보대화"),
    )
    if is_korean_defense_ministry_news(title, source) or official_personnel_news:
        return True
    headline_actor = current_government_actor(title)
    named_current_leader = _contains_any(title, CURRENT_GOVERNMENT_LEADER_KEYWORDS)
    if headline_actor is None and not named_current_leader:
        return False
    defense_context = (
        _contains_any(text, POLICY_KEYWORDS)
        or is_defense_business_news(text)
        or _is_defense_tech_policy_news(text)
        or _is_weapon_system_news(text)
    )
    defense_leader_context = headline_actor in CURRENT_DEFENSE_LEADER_KEYWORDS and (
        _contains_any(text, WEAPON_SYSTEM_KEYWORDS)
    )
    generic_presidential_context = headline_actor in {"대통령", "대통령실"} and (
        _contains_any(text, CURRENT_GOVERNMENT_POLICY_KEYWORDS)
    )
    generic_government_context = headline_actor == "정부" and _contains_any(
        text,
        GENERAL_GOVERNMENT_POLICY_KEYWORDS,
    )
    return (
        defense_context
        or (
            named_current_leader
            and _contains_any(text, CURRENT_GOVERNMENT_POLICY_KEYWORDS)
        )
        or defense_leader_context
        or generic_presidential_context
        or generic_government_context
    )


def _freshness_cutoff(now: datetime, *, days: int) -> datetime:
    kst_now = now.astimezone(KST)
    send_anchor = datetime.combine(kst_now.date(), SEND_WINDOW_START)
    return (send_anchor - timedelta(days=days)).astimezone(UTC)


def _is_defense_tech_policy_news(text: str) -> bool:
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


def _is_weapon_system_news(text: str, *, source: str = "") -> bool:
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


def _has_acquisition_policy_topic(text: str) -> bool:
    return _contains_any(text, ACQUISITION_POLICY_TERMS) and contains_defense_anchor(
        text
    )


def _has_acquisition_fact(text: str) -> bool:
    return _contains_any(text, ACQUISITION_FACT_TERMS) and (
        bool(matching_weapons(text))
        or _contains_any(text, ("무기체계", "국방획득", "국방조달", "유도무기", "군용"))
        or _has_acquisition_policy_topic(text)
    )


def _is_defense_leadership_appointment(title: str) -> bool:
    return (
        current_government_actor(title) in {"대통령", "대통령실"}
        and _contains_any(title, ("임명", "지명"))
        and _contains_any(title, CURRENT_DEFENSE_LEADER_KEYWORDS)
    )


def _is_weapon_development_title(title: str, *, source: str) -> bool:
    return _is_weapon_system_news(title.casefold(), source=source) and _contains_any(
        title,
        (
            "국내개발",
            "국내 개발",
            "체계개발",
            "개발 착수",
            "초도양산",
            "전력화 완료",
            "시험평가 완료",
        ),
    )


def _is_civilian_site_housing(title: str) -> bool:
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


def _is_public_procurement_headline(title: str) -> bool:
    return _contains_any(
        title,
        ("공공사업", "공공 소프트웨어", "공공SW", "대참제", "입찰제도", "조달제도"),
    )


def _has_unrelated_headline(title: str, description: str) -> bool:
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
        r"방산\s*주|%\s*[↑↓]|%대?\s*(?:강세|약세)|종목|급등|급락|상한가|하한가", title
    )
    recruiting = _contains_any(title, ("채용", "취업박람회", "취업 박람회"))
    civilian_local = _contains_any(title, ("분양", "공약사업")) and not _contains_any(
        title,
        ("국방", "방산", "병영", "군 숙소", "군 관사", "군인 아파트"),
    )
    if (
        financing or profile or stock_movement or recruiting or civilian_local
    ) and not _has_acquisition_fact(title):
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
        or _is_public_procurement_headline(title)
    )
    return incidental_agency and not headline_context
