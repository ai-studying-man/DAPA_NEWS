"""Current-government actor and policy classification rules."""

import re
from typing import Final

GOVERNMENT_ACTOR_KEYWORDS: Final[tuple[str, ...]] = (
    "이재명 대통령",
    "이 대통령",
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

CURRENT_GOVERNMENT_POLICY_KEYWORDS: Final[tuple[str, ...]] = (
    "국무회의",
    "업무보고",
    "국정성과",
    "국정과제",
    "국민참여",
    "기본법",
    "시행령",
)

GENERAL_GOVERNMENT_POLICY_KEYWORDS: Final[tuple[str, ...]] = (
    "업무보고",
    "국정성과",
    "국정과제",
    "국민참여",
)

CURRENT_GOVERNMENT_LEADER_KEYWORDS: Final[tuple[str, ...]] = (
    "이재명 대통령",
    "이 대통령",
    "대통령실",
)

CURRENT_DEFENSE_LEADER_KEYWORDS: Final[tuple[str, ...]] = (
    "국방장관",
    "합참의장",
    "육군참모총장",
    "해군참모총장",
    "공군참모총장",
)


def generic_current_government_actor(title: str) -> str | None:
    """Return a generic domestic-government actor leading the headline."""
    match = re.match(
        r"^(?:\[[^\]]+\]\s*)*(대통령실|대통령|정부)(?=$|[\s,:·은이가])",
        title.strip().casefold(),
    )
    return match.group(1) if match is not None else None
