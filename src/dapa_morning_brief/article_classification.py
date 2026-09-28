"""Resolve article relevance and its primary newsletter topic."""

from __future__ import annotations

from dapa_morning_brief.article_scope import (
    KOREAN_OFFICIAL_SOURCE_KEYWORDS,
    article_scope_is_allowed,
    has_foreign_primary_authority,
    is_korean_defense_ministry_news,
    is_us_defense_institution_news,
)
from dapa_morning_brief.business_rules import (
    contains_defense_anchor,
    is_company_social_event,
    is_defense_business_headline,
    is_defense_business_news,
    is_defense_export_news,
    is_foreign_procurement_news,
)
from dapa_morning_brief.entity_catalog import SOLDIER_SERVICE_ALIASES
from dapa_morning_brief.entity_catalog import contains_any as _contains_any
from dapa_morning_brief.government_rules import (
    CURRENT_DEFENSE_LEADER_KEYWORDS,
    CURRENT_GOVERNMENT_LEADER_KEYWORDS,
    CURRENT_GOVERNMENT_POLICY_KEYWORDS,
    GENERAL_GOVERNMENT_POLICY_KEYWORDS,
    current_government_actor,
)
from dapa_morning_brief.headline_rules import (
    has_acquisition_accountability_topic,
    has_acquisition_fact,
    has_acquisition_policy_topic,
    has_unrelated_headline,
    is_civilian_site_housing,
    is_defense_leadership_appointment,
    is_defense_tech_policy_news,
    is_military_security_incident,
    is_public_procurement_headline,
    is_weapon_development_title,
    is_weapon_system_news,
)
from dapa_morning_brief.models import Section
from dapa_morning_brief.sources import (
    EXCLUDE_KEYWORDS,
    POLICY_KEYWORDS,
    SOFT_EXCLUDE_KEYWORDS,
    UNTRUSTED_SOURCE_KEYWORDS,
    UNTRUSTED_TITLE_PREFIXES,
    WEAPON_SYSTEM_KEYWORDS,
)
from dapa_morning_brief.topic_boundaries import (
    has_unrelated_foreign_subject,
    is_defense_public_action,
    is_incidental_civic_agenda,
    is_military_equipment_overview,
    is_opinion_headline,
    is_overseas_delivery,
    is_overseas_weapon_use,
)


def classify_title(
    title: str,
    *,
    description: str = "",
    source: str = "",
) -> Section | None:
    """Prefer the headline's topic; use snippets only to resolve missing context."""
    if (
        is_opinion_headline(title)
        or (
            has_unrelated_foreign_subject(title)
            and not is_us_defense_institution_news(title)
        )
        or is_incidental_civic_agenda(title, description)
    ):
        return None
    service_policy = _contains_any(title, SOLDIER_SERVICE_ALIASES) and _contains_any(
        title,
        (
            "조달",
            "입찰",
            "계약",
            "보안 결함",
            "보안결함",
            "보안 취약점",
            "보안취약점",
            "정보 유출",
            "정보유출",
        ),
    )
    if service_policy or has_acquisition_accountability_topic(title, description):
        return Section.POLICY
    if is_military_equipment_overview(title) and not (
        has_acquisition_policy_topic(title) or is_public_procurement_headline(title)
    ):
        return Section.WEAPON_SYSTEM
    if (
        is_overseas_delivery(title, description)
        or is_overseas_weapon_use(title)
        or is_foreign_procurement_news(title, f"{title} {description}")
    ):
        return Section.EXPORT_BUSINESS
    headline_section = _classify_topic(title, title.casefold(), source)
    if headline_section is not None:
        return headline_section
    return _classify_topic(title, f"{title} {description}".casefold(), source)


def _classify_topic(title: str, text: str, source: str) -> Section | None:
    """Return no category when metadata provides no positive topic evidence."""
    if is_company_social_event(title):
        section = Section.EXPORT_BUSINESS
    elif has_acquisition_policy_topic(title) or is_public_procurement_headline(title):
        section = Section.POLICY
    elif is_current_government_news(text, title, source):
        section = Section.GOVERNMENT
    elif (
        is_defense_business_headline(title)
        or is_defense_export_news(text)
        or is_foreign_procurement_news(title, text)
    ):
        section = Section.EXPORT_BUSINESS
    elif is_weapon_development_title(title, source=source):
        section = Section.WEAPON_SYSTEM
    elif is_defense_tech_policy_news(text):
        section = Section.POLICY
    elif is_weapon_system_news(text, source=source):
        section = Section.WEAPON_SYSTEM
    elif _contains_any(text, (*POLICY_KEYWORDS, "방위정책")):
        section = Section.POLICY
    elif is_defense_business_news(text):
        section = Section.EXPORT_BUSINESS
    else:
        return None
    return section


def is_relevant_title(title: str) -> bool:
    """Return whether a title is relevant enough for DAPA morning brief."""
    return is_relevant_article(title, "", "")


def is_relevant_article(title: str, description: str, source: str) -> bool:
    """Return whether available RSS metadata is relevant to the brief."""
    text = f"{title} {description}".casefold()
    normalized_title = title.strip().casefold()
    headline_context = (
        contains_defense_anchor(title)
        or is_defense_business_news(normalized_title)
        or is_weapon_system_news(normalized_title, source=source)
        or is_defense_business_headline(title)
        or is_company_social_event(title)
        or is_current_government_news(normalized_title, title, source)
        or (is_public_procurement_headline(title) and contains_defense_anchor(text))
    )
    if (
        not headline_context
        or has_unrelated_foreign_subject(title)
        or is_incidental_civic_agenda(title, description)
        or is_opinion_headline(title)
        or normalized_title.startswith(UNTRUSTED_TITLE_PREFIXES)
        or _contains_any(
            source.casefold(),
            UNTRUSTED_SOURCE_KEYWORDS,
        )
        or has_unrelated_headline(title, description)
    ):
        return False
    if (
        _contains_any(text, SOFT_EXCLUDE_KEYWORDS) or is_civilian_site_housing(title)
    ) and not (has_acquisition_fact(title) or is_defense_leadership_appointment(title)):
        return False
    if _contains_any(normalized_title, EXCLUDE_KEYWORDS):
        return False
    if is_company_social_event(title):
        return True
    if not article_scope_is_allowed(text, title, source):
        return False
    defense_export = is_defense_export_news(text) or is_foreign_procurement_news(
        title, text
    )
    return (
        is_current_government_news(text, title, source)
        or is_defense_business_headline(title)
        or is_company_social_event(title)
        or is_defense_tech_policy_news(text)
        or defense_export
        or _contains_any(text, POLICY_KEYWORDS)
        or is_weapon_system_news(text, source=source)
        or is_defense_business_news(text)
    )


def is_current_government_news(text: str, title: str, source: str) -> bool:
    """Identify current Korean government actions within the configured scope."""
    if has_foreign_primary_authority(title):
        return False
    public_action = is_defense_public_action(title)
    if not public_action and not article_scope_is_allowed(text, title, source):
        return False
    alliance_news = is_us_defense_institution_news(title) and _contains_any(
        title,
        ("한미동맹", "주한미군", "한미 연합"),
    )
    if public_action or alliance_news or is_defense_leadership_appointment(title):
        return True
    official_personnel_news = _contains_any(
        source, KOREAN_OFFICIAL_SOURCE_KEYWORDS
    ) and _contains_any(
        title,
        ("장병", "복무여건", "병영", "국방정책", "국방예산", "서울안보대화"),
    )
    soldier_service = _contains_any(title, SOLDIER_SERVICE_ALIASES) and (
        _contains_any(
            text,
            ("AI", "행정", "복지", "서비스", "성과공유", "성과 공유", "개통", "이용"),
        )
    )
    if (
        is_korean_defense_ministry_news(title, source)
        or is_military_security_incident(title)
        or official_personnel_news
        or soldier_service
    ):
        return True
    headline_actor = current_government_actor(title)
    named_current_leader = _contains_any(title, CURRENT_GOVERNMENT_LEADER_KEYWORDS)
    if headline_actor is None and not named_current_leader:
        return False
    defense_context = (
        _contains_any(text, POLICY_KEYWORDS)
        or is_defense_business_news(text)
        or is_defense_tech_policy_news(text)
        or is_weapon_system_news(text)
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
