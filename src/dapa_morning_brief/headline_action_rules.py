"""Distinguish market outreach from domestic military support procurement."""

import re

from dapa_morning_brief.business_rules import (
    DEFENSE_COMPANY_KEYWORDS,
    is_defense_business_news,
    is_defense_export_news,
)
from dapa_morning_brief.entity_catalog import SOLDIER_SERVICE_ALIASES, contains_any
from dapa_morning_brief.weapon_catalog import matching_weapons


def is_domestic_support_contract(title: str, context: str) -> bool:
    """Require military support procurement and a domestic acquiring authority."""
    return (
        contains_any(title, ("군수지원", "PBL", "성과기반"))
        and contains_any(title, ("계약", "조달", "입찰"))
        and contains_any(context, ("방위사업청", "방사청", "우리 군", "국군"))
        and not is_defense_export_news(title)
    )


def is_defense_market_outreach(title: str) -> bool:
    """Require defense identity and a primary market-development action."""
    defense_identity = is_defense_business_news(title) or (
        bool(matching_weapons(title)) and contains_any(title, DEFENSE_COMPANY_KEYWORDS)
    )
    return defense_identity and bool(
        re.search(r"시장\s*(?:공략|진출|개척)|수출\s*(?:마케팅|판로)", title)
    )


def is_soldier_service_procurement(title: str) -> bool:
    """Separate soldier-service procurement scrutiny from ordinary welfare news."""
    return contains_any(title, SOLDIER_SERVICE_ALIASES) and contains_any(
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
