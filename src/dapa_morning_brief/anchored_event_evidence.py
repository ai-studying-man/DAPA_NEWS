"""Match translated flight reports using explicit event facts, not weapon topics."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from dapa_morning_brief.story_signals import title_tokens
from dapa_morning_brief.weapon_catalog import matching_weapons

MONTHS: Final = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)
LEAD_LIMIT: Final = 120
MIN_OPENING_ANCHORS: Final = 3
MIN_FLIGHT_MODELS: Final = 2
FLIGHT_LOCATIONS: Final = (
    ("고흥", "goheung"),
    ("사천", "sacheon"),
    ("서산", "seosan"),
    ("청주", "cheongju"),
    ("원주", "wonju"),
    ("군산", "gunsan"),
)
OPENING_LOCATIONS: Final = (
    ("판교", "pangyo"),
    ("대전", "daejeon"),
    ("부산", "busan"),
    ("양재", "yangjae"),
    ("용산", "yongsan"),
)


@dataclass(frozen=True, slots=True)
class EventEvidence:
    """Pair event text with the publication date used for relative-date parsing."""

    text: str
    published_at: datetime


def compare_opening_leads(left: str, right: str) -> bool | None:
    """Use dated opening leads while excluding lengthy shared background."""
    first = " ".join(left.split()[:LEAD_LIMIT])
    second = " ".join(right.split()[:LEAD_LIMIT])
    if not all("개소" in text for text in (first, second)):
        return None
    dates = (
        set(re.findall(r"(\d{1,2})일", first)),
        set(re.findall(r"(\d{1,2})일", second)),
    )
    if dates[0] and dates[1] and dates[0].isdisjoint(dates[1]):
        return False
    locations = (
        _primary_opening_site(first.casefold()),
        _primary_opening_site(second.casefold()),
    )
    if locations[0] and locations[1] and locations[0] != locations[1]:
        return False
    shared = title_tokens(first) & title_tokens(second)
    specific = {
        token
        for token in shared
        if not token.isdigit()
        and token
        not in {"일", "국방부", "정부", "개소", "개소식", "개최", "첫", "거점"}
    }
    if (
        dates[0] & dates[1]
        and len(specific) >= MIN_OPENING_ANCHORS
        and locations[0] is not None
        and locations[0] == locations[1]
    ):
        return True
    return None


def compare_formation_events(left: EventEvidence, right: EventEvidence) -> bool | None:
    """Require joint-flight subjects, event date and duration across languages."""
    first = " ".join(left.text.split()[:LEAD_LIMIT]).casefold()
    second = " ".join(right.text.split()[:LEAD_LIMIT]).casefold()
    actions = ("편대비행", "편대 비행", "formation flight")
    if not all(any(action in text for action in actions) for text in (first, second)):
        return None
    dates = (
        _event_dates(first, left.published_at),
        _event_dates(second, right.published_at),
    )
    if dates[0] and dates[1] and dates[0].isdisjoint(dates[1]):
        return False
    models = _models(first) & _models(second)
    locations = (
        _locations(first, FLIGHT_LOCATIONS),
        _locations(second, FLIGHT_LOCATIONS),
    )
    if locations[0] and locations[1] and locations[0].isdisjoint(locations[1]):
        return False
    durations = _durations(first), _durations(second)
    if durations[0] and durations[1] and durations[0].isdisjoint(durations[1]):
        return False
    if (
        len(models) >= MIN_FLIGHT_MODELS
        and dates[0] & dates[1]
        and durations[0] & durations[1]
        and locations[0] & locations[1]
    ):
        return True
    return None


def _event_dates(text: str, published: datetime) -> frozenset[tuple[int, int]]:
    korean = {
        (int(match[1]), int(match[2]))
        for match in re.finditer(r"(\d{1,2})월\s*(\d{1,2})일", text)
    }
    english = {
        (index, int(match[1]))
        for index, month in enumerate(MONTHS, start=1)
        for match in re.finditer(rf"\b{month}\s+(\d{{1,2}})\b", text)
    }
    if not korean:
        korean = {
            (published.month, int(match[1]))
            for match in re.finditer(r"지난\s*(\d{1,2})일", text)
            if int(match[1]) <= published.day
        }
    return frozenset(korean | english)


def _models(text: str) -> frozenset[str]:
    models = {entry.identifier for entry in matching_weapons(text)}
    models.update(
        match[0] for match in re.finditer(r"(?<![a-z0-9])aap(?![a-z0-9])", text)
    )
    return frozenset(models)


def _durations(text: str) -> frozenset[int]:
    return frozenset(
        int(match[1]) for match in re.finditer(r"(\d+)\s*(?:분|minutes?\b)", text)
    )


def _locations(text: str, aliases: tuple[tuple[str, str], ...]) -> frozenset[str]:
    return frozenset(
        korean
        for korean, english in aliases
        if korean in text or re.search(rf"\b{english}\b", text)
    )


def _primary_opening_site(text: str) -> str | None:
    occurrences = [
        (match.start(), korean)
        for korean, english in OPENING_LOCATIONS
        for match in re.finditer(rf"{korean}|\b{english}\b", text)
    ]
    return min(occurrences)[1] if occurrences else None
