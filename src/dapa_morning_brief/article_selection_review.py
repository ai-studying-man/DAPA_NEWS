"""Review extracted evidence before an article consumes a final section slot."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from dapa_morning_brief.article_classification import (
    classify_title,
    is_relevant_article,
)
from dapa_morning_brief.article_scope import KOREAN_OFFICIAL_SOURCE_KEYWORDS
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


@dataclass(frozen=True, slots=True)
class SelectionReview:
    """Keep missing-body decisions distinct from body-backed review decisions."""

    article: Article | None
    reason: str


def review_selection(article: Article, body: str) -> SelectionReview:
    """Revisit category using the headline and lead, never the article's tail."""
    if not body.strip():
        return SelectionReview(article, "body_unavailable")
    lead = body[:800]
    section = classify_title(article.title, description=lead, source=article.source)
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
    if civilian_primary_topic or (
        article.search_provider
        and not headline_defense_identity
        and not is_relevant_article(article.title, lead, article.source)
    ):
        return SelectionReview(None, "body_review_unrelated")
    if is_overseas_delivery(article.title, body) or is_overseas_weapon_use(
        article.title, body
    ):
        return SelectionReview(
            replace(article, section=Section.EXPORT_BUSINESS), "overseas_body_reviewed"
        )
    if section is None:
        return SelectionReview(article, "category_unresolved")
    primary_section = _primary_action_section(article.title, lead)
    if primary_section is not None:
        section = primary_section
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
        return SelectionReview(article, "category_preserved")
    return SelectionReview(replace(article, section=section), "body_reviewed")


def _primary_action_section(title: str, lead: str) -> Section | None:
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
