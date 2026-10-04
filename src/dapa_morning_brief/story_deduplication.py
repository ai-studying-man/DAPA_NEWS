"""Compare news events before category quotas are applied."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from dapa_morning_brief.appointment_evidence import compare_appointment_leads
from dapa_morning_brief.article_history import canonical_url
from dapa_morning_brief.body_similarity import has_substantial_body, have_similar_bodies
from dapa_morning_brief.entity_catalog import (
    COMPANY_ALIASES,
    SOLDIER_SERVICE_ALIASES,
    contains_any,
)
from dapa_morning_brief.event_evidence import (
    have_concordant_event_leads,
    have_conflicting_quantities,
    have_distinct_weapons,
    have_near_identical_headlines,
    have_shared_short_event,
)
from dapa_morning_brief.story_signals import (
    EVENT_ACTION_TOKENS,
    EVENT_CONTEXT_TOKEN_GROUPS,
    EVENT_MARKET_TOKENS,
    MIN_CONTAINMENT_RATIO,
    MIN_DESCRIPTION_CONTAINMENT_RATIO,
    MIN_DESCRIPTION_SHARED_TOKENS,
    MIN_EVENT_SUBJECT_TOKEN_LENGTH,
    MIN_SHARED_CONTEXT_TOKENS,
    MIN_SHARED_TOKENS,
    NEGATIVE_EVENT_OUTCOME_TOKENS,
    POSITIVE_EVENT_OUTCOME_TOKENS,
    known_event_key,
    normalize_title,
    series_key,
    title_tokens,
)

if TYPE_CHECKING:
    from dapa_morning_brief.models import Article


def are_same_story(left_title: str, right_title: str) -> bool:
    """Return whether two differently worded titles describe one event."""
    if (
        have_distinct_weapons(left_title, right_title)
        or have_conflicting_quantities(left_title, right_title)
        or _have_conflicting_event_facts(
            title_tokens(left_title),
            title_tokens(right_title),
        )
    ):
        return False
    left_normalized = normalize_title(left_title)
    right_normalized = normalize_title(right_title)
    left_series = series_key(left_title)
    right_series = series_key(right_title)
    left_known_event = known_event_key(left_normalized)
    right_known_event = known_event_key(right_normalized)
    if (
        left_normalized == right_normalized
        or (left_series is not None and left_series == right_series)
        or (left_known_event is not None and left_known_event == right_known_event)
    ):
        return True

    left_tokens = title_tokens(left_title)
    right_tokens = title_tokens(right_title)
    if left_tokens == right_tokens:
        return True

    shared_tokens = left_tokens & right_tokens
    shares_event_subject = any(
        len(token) >= MIN_EVENT_SUBJECT_TOKEN_LENGTH for token in shared_tokens
    )
    if (
        shares_event_subject
        and (
            (left_tokens & EVENT_ACTION_TOKENS and right_tokens & EVENT_ACTION_TOKENS)
            or len(shared_tokens) >= MIN_SHARED_CONTEXT_TOKENS
        )
    ) or (
        len(shared_tokens) >= MIN_SHARED_CONTEXT_TOKENS
        and any(
            left_tokens & context_tokens and right_tokens & context_tokens
            for context_tokens in EVENT_CONTEXT_TOKEN_GROUPS
        )
    ):
        return True
    if len(shared_tokens) < MIN_SHARED_TOKENS:
        return False

    shorter_token_count = min(len(left_tokens), len(right_tokens))
    containment_ratio = len(shared_tokens) / shorter_token_count
    return containment_ratio >= MIN_CONTAINMENT_RATIO or bool(
        shared_tokens & EVENT_ACTION_TOKENS,
    )


def _have_conflicting_event_facts(
    left_tokens: frozenset[str],
    right_tokens: frozenset[str],
) -> bool:
    left_markets = left_tokens & EVENT_MARKET_TOKENS
    right_markets = right_tokens & EVENT_MARKET_TOKENS
    different_markets = (
        left_markets and right_markets and left_markets.isdisjoint(right_markets)
    )
    conflicting_outcomes = (
        left_tokens & POSITIVE_EVENT_OUTCOME_TOKENS
        and right_tokens & NEGATIVE_EVENT_OUTCOME_TOKENS
    ) or (
        right_tokens & POSITIVE_EVENT_OUTCOME_TOKENS
        and left_tokens & NEGATIVE_EVENT_OUTCOME_TOKENS
    )
    delivery = frozenset({"인도", "납품", "배치", "전력화"})
    contract = frozenset({"계약", "체결", "수주"})
    different_stages = (
        left_tokens & delivery
        and not left_tokens & contract
        and right_tokens & contract
        and not right_tokens & delivery
    ) or (
        right_tokens & delivery
        and not right_tokens & contract
        and left_tokens & contract
        and not left_tokens & delivery
    )
    briefing = frozenset({"브리핑", "기자회견"})
    visit = frozenset({"방문", "시찰", "점검", "위문"})
    different_public_actions = (
        left_tokens & briefing
        and not left_tokens & visit
        and right_tokens & visit
        and not right_tokens & briefing
    ) or (
        right_tokens & briefing
        and not right_tokens & visit
        and left_tokens & visit
        and not left_tokens & briefing
    )
    return bool(
        different_markets
        or conflicting_outcomes
        or different_stages
        or different_public_actions
    )


def are_same_articles(
    left: Article,
    right: Article,
    *,
    left_body: str = "",
    right_body: str = "",
) -> bool:
    """Compare article titles, RSS descriptions, and extracted bodies."""
    if canonical_url(left.url) == canonical_url(right.url):
        return True
    if (
        have_distinct_weapons(left.title, right.title)
        or have_conflicting_quantities(left.title, right.title, rounds_only=True)
        or _have_conflicting_event_facts(
            title_tokens(left.title),
            title_tokens(right.title),
        )
        or abs(left.published_at - right.published_at) > timedelta(days=2)
    ):
        return False
    appointment = compare_appointment_leads(
        left.title,
        right.title,
        left_body or left.description,
        right_body or right.description,
    )
    if appointment is not None or have_conflicting_quantities(left.title, right.title):
        return (
            appointment
            if appointment is not None
            else bool(
                left_body and right_body and have_similar_bodies(left_body, right_body)
            )
        )
    if have_near_identical_headlines(left.title, right.title):
        return True
    if has_substantial_body(left_body) and has_substantial_body(right_body):
        return have_similar_bodies(left_body, right_body) or (
            have_shared_short_event(
                f"{left.title} {left.description}",
                f"{right.title} {right.description}",
            )
            and have_concordant_event_leads(left_body, right_body)
        )
    left_event = _event_fingerprint(left.title, f"{left.description} {left_body}")
    right_event = _event_fingerprint(right.title, f"{right.description} {right_body}")
    left_tokens = title_tokens(left.description)
    right_tokens = title_tokens(right.description)
    shared_tokens = left_tokens & right_tokens
    shorter_token_count = min(len(left_tokens), len(right_tokens))
    similar_description = (
        len(shared_tokens) >= MIN_DESCRIPTION_SHARED_TOKENS
        and len(shared_tokens) / shorter_token_count
        >= MIN_DESCRIPTION_CONTAINMENT_RATIO
    )
    return (
        are_same_story(left.title, right.title)
        or have_shared_short_event(
            f"{left.title} {left_body or left.description}",
            f"{right.title} {right_body or right.description}",
        )
        or bool(
            left_body and right_body and have_shared_short_event(left_body, right_body)
        )
        or (left_event is not None and left_event == right_event)
        or bool(left_body and right_body and have_similar_bodies(left_body, right_body))
        or similar_description
    )


def _event_fingerprint(title: str, description: str) -> str | None:
    text = f"{title} {description}"
    if (
        contains_any(title, ("대전",))
        and contains_any(title, ("육군",))
        and contains_any(title, ("AX", "AI", "인공지능 전환"))
        and contains_any(text, ("협력체계", "대덕경찰서", "AX 대전 거점"))
    ):
        return "육군-대전-ax협력거점"
    if (
        (
            contains_any(title, (*SOLDIER_SERVICE_ALIASES, "장병용 AI"))
            or (
                contains_any(title, ("국방부 최초 민간 클라우드",))
                and contains_any(text, SOLDIER_SERVICE_ALIASES)
            )
        )
        and contains_any(text, ("AI",))
        and contains_any(
            text,
            (
                "가동",
                "출시",
                "개통",
                "시대 연다",
                "정식 서비스",
                "고도화",
                "탑재",
                "들어온다",
            ),
        )
        and not contains_any(title, ("취약", "유출", "장애", "중단"))
    ):
        return "장병이음-ai"
    company = next(
        (group[0] for group in COMPANY_ALIASES if contains_any(title, group)), None
    )
    markets = title_tokens(title) & EVENT_MARKET_TOKENS
    partnership = contains_any(
        title,
        (
            "MOU",
            "협력",
            "협약",
            "공급망",
            "시장 진출",
            "진출 추진",
            "현지화",
            "교두보",
            "supply chain",
            "local partners",
        ),
    ) and not contains_any(title, ("계약", "납품", "인도", "수주 확정"))
    counterparty = contains_any(
        text,
        (
            "FEMIA",
            "멕시코 항공우주산업협회",
            "멕시코항공우주산업협회",
        ),
    )
    if company and len(markets) == 1 and partnership and counterparty:
        return f"{company}:{next(iter(markets))}:femia-partnership"
    if (
        contains_any(title, ("기술교범", "교범"))
        and contains_any(title, ("확대", "표준화", "적용", "공유"))
        and contains_any(text, ("S1000D",))
    ):
        return "s1000d-manual-standardization"
    if (
        contains_any(title, ("한화",))
        and contains_any(
            text,
            ("힐링데이", "군인가족", "군인 가족", "모범군인", "모범장병"),
        )
        and contains_any(text, ("초청", "가족"))
    ):
        return "한화군인가족힐링데이"
    return None
