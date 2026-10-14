"""Admit ambiguous equipment headlines only after main-body evidence confirms them."""

from typing import Final

from dapa_morning_brief.article_classification import classify_title
from dapa_morning_brief.business_rules import contains_defense_anchor
from dapa_morning_brief.entity_catalog import contains_any
from dapa_morning_brief.headline_rules import (
    has_acquisition_fact,
    has_unrelated_headline,
    is_defense_leadership_appointment,
)
from dapa_morning_brief.models import Article, Section
from dapa_morning_brief.sources import (
    EXCLUDE_KEYWORDS,
    GENERIC_WEAPON_KEYWORDS,
    SOFT_EXCLUDE_KEYWORDS,
    UNTRUSTED_SOURCE_KEYWORDS,
    UNTRUSTED_TITLE_PREFIXES,
)
from dapa_morning_brief.topic_boundaries import (
    has_unrelated_foreign_subject,
    is_opinion_headline,
)

BODY_REVIEW_TERMS: Final = (
    *(term for term in GENERIC_WEAPON_KEYWORDS if term not in {"AI", "우주"}),
    "TICN",
    "TMMR",
    "전술정보통신체계",
)
MILITARY_ACTIONS: Final = (
    "도입",
    "납품",
    "구매",
    "계약",
    "조달",
    "입찰",
    "운용",
    "배치",
    "시험",
    "개발",
    "생산",
    "전력화",
    "훈련",
)
PROCUREMENT_ACTIONS: Final = ("도입", "납품", "구매", "계약", "조달", "입찰")
ACCOUNTABILITY_TERMS: Final = (
    "방치",
    "부실",
    "결함",
    "고장",
    "문제",
    "불가",
    "지연",
    "제재",
    "논란",
    "쓰지 못",
    "운용하지 못",
)
BODY_CONTEXT_LIMIT: Final = 1_600


def equipment_review_section(
    title: str, description: str, source: str
) -> Section | None:
    """Keep equipment leads for evidence review without accepting unrelated prose."""
    if (
        not contains_any(title, BODY_REVIEW_TERMS)
        or is_opinion_headline(title)
        or has_unrelated_headline(title, description)
        or has_unrelated_foreign_subject(title)
        or contains_any(source, UNTRUSTED_SOURCE_KEYWORDS)
        or title.strip().casefold().startswith(UNTRUSTED_TITLE_PREFIXES)
        or contains_any(title, EXCLUDE_KEYWORDS)
        or (
            contains_any(f"{title} {description}", SOFT_EXCLUDE_KEYWORDS)
            and not has_acquisition_fact(f"{title} {description}")
            and not is_defense_leadership_appointment(title)
        )
    ):
        return None
    return Section.WEAPON_SYSTEM


def confirmed_equipment_section(article: Article, body: str) -> Section | None:
    """Require military activity in the main narrative, not an incidental tail."""
    lead = body[:BODY_CONTEXT_LIMIT]
    context = f"{article.title} {lead}"
    if not (
        contains_defense_anchor(lead)
        and contains_any(context, BODY_REVIEW_TERMS)
        and contains_any(lead, MILITARY_ACTIONS)
    ):
        return None
    if is_body_acquisition_accountability(article.title, lead):
        return Section.POLICY
    return (
        classify_title(article.title, description=lead, source=article.source)
        or Section.WEAPON_SYSTEM
    )


def is_body_acquisition_accountability(title: str, body: str) -> bool:
    """Identify procurement scrutiny from body evidence rather than headline actors."""
    lead = body[:BODY_CONTEXT_LIMIT]
    context = f"{title} {lead}"
    return (
        contains_defense_anchor(lead)
        and contains_any(context, BODY_REVIEW_TERMS)
        and contains_any(lead, PROCUREMENT_ACTIONS)
        and contains_any(context, ACCOUNTABILITY_TERMS)
    )
