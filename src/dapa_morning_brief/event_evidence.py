"""Combine headline and short-caption evidence without treating topics as events."""

import re
from difflib import SequenceMatcher
from typing import Final

from dapa_morning_brief.story_signals import normalize_title, title_tokens
from dapa_morning_brief.weapon_catalog import matching_weapons

MIN_HEADLINE_LENGTH: Final = 16
MIN_HEADLINE_SIMILARITY: Final = 0.94
MIN_EVENT_OVERLAP: Final = 0.35
MIN_EVENT_SHARED_TOKENS: Final = 3
CONTEXT_WORD_LIMIT: Final = 60
GENERIC_CONTEXT: Final = frozenset(
    {
        "국방부",
        "합참",
        "정부",
        "차장",
        "장관",
        "기자",
        "서울",
        "용산구",
        "결과",
        "조사",
        "상황",
    }
)
EVENT_ACTIONS: Final = (
    "브리핑",
    "기자회견",
    "협약",
    "계약",
    "납품",
    "인도",
    "진수",
    "출범",
)


def have_distinct_weapons(left: str, right: str) -> bool:
    """Keep explicitly different weapon programs separate despite shared actions."""
    first = {entry.identifier for entry in matching_weapons(left)}
    second = {entry.identifier for entry in matching_weapons(right)}
    return bool(first and second and first.isdisjoint(second))


def have_conflicting_quantities(
    left: str, right: str, *, rounds_only: bool = False
) -> bool:
    """Veto fuzzy matches when explicit same-unit procurement facts disagree."""
    units = "차" if rounds_only else "차|문|대|척|기"
    pattern = rf"(?<![A-Za-z0-9])([0-9][0-9,]*)\s*({units})(?![가-힣A-Za-z0-9])"
    first = [(match[1], match[2]) for match in re.finditer(pattern, left)]
    second = [(match[1], match[2]) for match in re.finditer(pattern, right)]
    for unit in {unit for _, unit in first} & {unit for _, unit in second}:
        first_values = {
            int(value.replace(",", "")) for value, kind in first if kind == unit
        }
        second_values = {
            int(value.replace(",", "")) for value, kind in second if kind == unit
        }
        if first_values.isdisjoint(second_values):
            return True
    return False


def have_concordant_event_leads(left: str, right: str) -> bool:
    """Compare opening sentences so repeated background cannot establish the event."""
    first = re.split(r"[.!?]\s|\n", left, maxsplit=1)[0]
    second = re.split(r"[.!?]\s|\n", right, maxsplit=1)[0]
    return have_shared_short_event(first, second)


def have_near_identical_headlines(left: str, right: str) -> bool:
    """Allow almost-exact titles as evidence even when body extraction differs."""
    label = r"\[(?:종합\d*|속보|사진|포토|단독)\]"
    first = normalize_title(re.sub(label, "", left))
    second = normalize_title(re.sub(label, "", right))
    return (
        min(len(first), len(second)) >= MIN_HEADLINE_LENGTH
        and SequenceMatcher(None, first, second, autojunk=False).ratio()
        >= MIN_HEADLINE_SIMILARITY
    )


def have_shared_short_event(left: str, right: str) -> bool:
    """Require a shared action and specific subjects in combined short evidence."""
    first, second = _normalize_event_text(left), _normalize_event_text(right)
    if not any(action in first and action in second for action in EVENT_ACTIONS):
        return False
    first_tokens = title_tokens(first) - GENERIC_CONTEXT
    second_tokens = title_tokens(second) - GENERIC_CONTEXT
    shared = first_tokens & second_tokens
    shorter = min(len(first_tokens), len(second_tokens))
    return (
        len(shared) >= MIN_EVENT_SHARED_TOKENS
        and len(shared) / shorter >= MIN_EVENT_OVERLAP
    )


def _normalize_event_text(text: str) -> str:
    normalized = " ".join(text.split()[:CONTEXT_WORD_LIMIT]).casefold()
    for original, replacement in (
        ("비무장지대", "dmz"),
        ("합동참모본부", "합참"),
        ("매설지뢰", "매설 지뢰"),
        ("폭발사고", "폭발 사고"),
    ):
        normalized = normalized.replace(original, replacement)
    return normalized
