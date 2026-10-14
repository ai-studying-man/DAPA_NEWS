"""Review extracted evidence before an article consumes a final section slot."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from dapa_morning_brief.article_classification import (
    classify_title,
    is_relevant_article,
)
from dapa_morning_brief.article_scope import (
    FOREIGN_PRIMARY_COUNTRIES,
    KOREAN_OFFICIAL_SOURCE_KEYWORDS,
    STRONG_KOREAN_SCOPE_KEYWORDS,
)
from dapa_morning_brief.body_relevance import (
    confirmed_equipment_section,
    is_body_acquisition_accountability,
)
from dapa_morning_brief.business_rules import contains_defense_anchor
from dapa_morning_brief.entity_catalog import contains_any
from dapa_morning_brief.headline_action_rules import (
    is_defense_market_outreach,
    is_domestic_support_contract,
)
from dapa_morning_brief.models import Section
from dapa_morning_brief.topic_boundaries import (
    is_overseas_delivery,
    is_overseas_weapon_use,
)
from dapa_morning_brief.weapon_catalog import matching_weapons

if TYPE_CHECKING:
    from dapa_morning_brief.models import Article


FOREIGN_AUTHORITY: Final[re.Pattern[str]] = re.compile(
    "".join(
        (
            r"(?:",
            "|".join((*FOREIGN_PRIMARY_COUNTRIES, "미국", "영국", "프랑스", "독일")),
            r")",
            r"(?:의)?\s*(?:내\b|정부|대통령|국방|육군|해군|공군|군\b)",
            r"|(?:미|美)\s*(?:국방|대통령|육군|해군|공군)",
            r"|\b(?:U\.S\.|US|United States)\s+(?:Army|Navy|Air Force|government)",
        )
    ),
    re.IGNORECASE,
)


class ReviewStatus(StrEnum):
    """Separate explicit rejection from missing or uncertain evidence."""

    ACCEPTED = "accepted"
    UNRELATED = "unrelated"
    CATEGORY_UNCERTAIN = "category_uncertain"
    RELEVANCE_UNCERTAIN = "relevance_uncertain"
    BODY_UNAVAILABLE = "body_unavailable"


@dataclass(frozen=True, slots=True)
class SelectionReview:
    """Keep missing-body decisions distinct from body-backed review decisions."""

    article: Article | None
    reason: str
    status: ReviewStatus = ReviewStatus.ACCEPTED


def review_selection(article: Article, body: str) -> SelectionReview:
    """Revisit category using the headline and lead, never the article's tail."""
    if not body.strip():
        return SelectionReview(
            None if article.requires_body_review else article,
            "body_unavailable",
            ReviewStatus.BODY_UNAVAILABLE,
        )
    relevance = _review_relevance(article, body)
    if relevance is not None:
        return relevance
    lead = body[:800]
    section = classify_title(article.title, description=lead, source=article.source)
    if is_overseas_delivery(article.title, body) or is_overseas_weapon_use(
        article.title, body
    ):
        return SelectionReview(
            replace(article, section=Section.EXPORT_BUSINESS), "overseas_body_reviewed"
        )
    primary_section = _primary_action_section(article.title, lead)
    if primary_section is not None:
        section = primary_section
    if section is None:
        return SelectionReview(
            article, "category_unresolved", ReviewStatus.CATEGORY_UNCERTAIN
        )
    correction_evidence = (
        primary_section is not None
        or (
            contains_any(article.source, KOREAN_OFFICIAL_SOURCE_KEYWORDS)
            and contains_any(
                article.title, ("장병", "복무", "병영", "국방정책", "국방예산")
            )
        )
        or is_defense_market_outreach(article.title)
        or is_domestic_support_contract(article.title, lead)
    )
    if not correction_evidence:
        status = (
            ReviewStatus.CATEGORY_UNCERTAIN
            if section is not article.section
            else ReviewStatus.ACCEPTED
        )
        return SelectionReview(article, "category_preserved", status)
    return SelectionReview(replace(article, section=section), "body_reviewed")


def _review_relevance(article: Article, body: str) -> SelectionReview | None:
    lead = body[:800]
    context = f"{article.title} {lead}"
    korean_connection = contains_any(
        context,
        (*STRONG_KOREAN_SCOPE_KEYWORDS, "한미", "국군", "우리 군", "Hanwha", "Rotem"),
    ) or bool(matching_weapons(context))
    primary_lead = re.sub(r"^(?:\[[^\]]+\]\s*)*", "", body.strip())[:300]
    if FOREIGN_AUTHORITY.match(primary_lead) and not korean_connection:
        return SelectionReview(None, "foreign_body_unrelated", ReviewStatus.UNRELATED)
    civilian_primary_topic = (
        contains_any(article.title, ("작물", "재배", "토양", "농업", "농촌"))
        and contains_any(lead, ("약용작물", "재배", "토양", "농촌진흥청"))
        and not (
            contains_defense_anchor(article.title)
            or contains_any(article.title, ("미사일", "지대공", "요격", "자주포"))
        )
    )
    headline_defense_identity = contains_defense_anchor(article.title) or bool(
        matching_weapons(article.title)
    )
    if civilian_primary_topic:
        return SelectionReview(None, "body_review_unrelated", ReviewStatus.UNRELATED)
    if article.requires_body_review:
        section = confirmed_equipment_section(article, body)
        if section is None:
            return SelectionReview(
                None, "body_review_insufficient", ReviewStatus.RELEVANCE_UNCERTAIN
            )
        return SelectionReview(
            replace(article, section=section, requires_body_review=False),
            "body_relevance_confirmed",
        )
    if (
        article.search_provider
        and not headline_defense_identity
        and not is_relevant_article(article.title, lead, article.source)
    ):
        return SelectionReview(
            article, "relevance_uncertain", ReviewStatus.RELEVANCE_UNCERTAIN
        )
    return None


def _primary_action_section(title: str, lead: str) -> Section | None:
    if is_body_acquisition_accountability(title, lead):
        return Section.POLICY
    parliamentary_resolution = (
        contains_any(title, ("국회", "국방위"))
        and contains_any(title, ("결의안", "규탄결의"))
        and contains_any(title, ("채택", "의결", "표결", "발의"))
        and contains_any(lead, ("국방위", "국방부", "장병", "북한", "北"))
        and contains_any(lead, ("결의안", "규탄결의"))
    )
    alliance_policy = (
        re.match(r"^(?:\[[^\]]+\]\s*)*(?:미국|미|美)\s*국방", title) is not None
        and contains_any(title, ("주한미군", "한미동맹", "한미 연합"))
        and contains_any(title, ("준비태세", "복지", "인사", "정책", "전략"))
        and contains_any(lead, ("주한미군", "한미동맹", "한미 연합"))
        and contains_any(lead, ("준비태세", "복지", "인사", "정책", "전략"))
        and not contains_any(
            title, ("개발", "시험", "양산", "성능개량", "도입", "계약", "조달")
        )
    )
    if parliamentary_resolution or alliance_policy:
        return Section.GOVERNMENT
    regulatory_action = (
        contains_defense_anchor(title)
        and contains_any(title, ("미허가", "위반", "불법", "안전점검", "안전 점검"))
        and contains_any(lead, ("정부", "방위사업청", "방사청", "고용노동부", "소방청"))
        and contains_any(lead, ("점검", "적발", "제재", "허가"))
    )
    if regulatory_action:
        return Section.POLICY
    domestic_development = (
        contains_any(title, ("개발", "시험", "성능개량"))
        and (
            bool(matching_weapons(lead))
            or contains_any(lead, ("무기 체계", "무기체계", "근접방어", "수직발사"))
        )
        and contains_any(lead, ("국내", "우리", "국산", "한국형", "독자 기술"))
        and contains_any(lead, ("개발", "시험", "성능개량"))
        and not contains_any(
            title, ("수출 계약", "수출계약", "수주", "납품", "해외 공급")
        )
    )
    if domestic_development:
        return Section.WEAPON_SYSTEM
    return None
