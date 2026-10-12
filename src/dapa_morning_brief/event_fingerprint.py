"""Reviewed event identities shared by article duplicate matching."""

from dapa_morning_brief.entity_catalog import (
    COMPANY_ALIASES,
    SOLDIER_SERVICE_ALIASES,
    contains_any,
)
from dapa_morning_brief.story_signals import EVENT_MARKET_TOKENS, title_tokens


def event_fingerprint(title: str, description: str) -> str | None:
    """Return a reviewed event identity from headline and supporting text."""
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
