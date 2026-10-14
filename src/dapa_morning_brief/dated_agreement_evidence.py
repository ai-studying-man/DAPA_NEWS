"""Conservative dated agreement evidence, compact enough for collection history."""

import re
from datetime import date, datetime
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict

from dapa_morning_brief.story_signals import title_tokens
from dapa_morning_brief.weapon_catalog import matching_weapons

MIN_SUBJECT_LENGTH: Final = 3
MIN_SHARED_SUBJECTS: Final = 5
MIN_SUBJECT_OVERLAP: Final = 0.15
MIN_UNNAMED_SHARED_SUBJECTS: Final = 8
MIN_UNNAMED_SUBJECT_OVERLAP: Final = 0.35
AGREEMENT_LOCATIONS: Final = (
    ("워싱턴", "washington"),
    ("서울", "seoul"),
    ("부산", "busan"),
    ("대전", "daejeon"),
    ("브로츠와프", "wroclaw"),
    ("바르샤바", "warsaw"),
)

AGREEMENTS: Final = ("협약", "mou", "기술협정", "기술지원협정", "teaming agreement")
MILESTONES: Final = (
    "계약",
    "납품",
    "인도",
    "진수",
    "발사",
    "시험 성공",
    "승인",
    "착공",
    "완공",
)
ANALYSIS: Final = ("기고", "사설", "칼럼", "기술 해설", "종합 분석")
GENERIC: Final = frozenset(
    {
        "지난",
        "현지",
        "현장",
        "미국",
        "방산",
        "개발",
        "협력",
        "시장",
        "체결",
        "협약",
        "업무협약",
        "기술협약",
        "밝혔다",
        "맺었다",
        "추진",
        "계획",
    }
)


class AgreementEvidence(BaseModel):
    """Persist event anchors only, never article sentences or full bodies."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")
    event_date: date
    subjects: tuple[str, ...]
    parties: tuple[str, ...] = ()
    weapons: tuple[str, ...] = ()
    locations: tuple[str, ...] = ()


def agreement_evidence(
    title: str, body: str, published: datetime
) -> AgreementEvidence | None:
    """Require a dated agreement lead and avoid independently new milestones."""
    if not body or any(marker in title for marker in (*MILESTONES, *ANALYSIS)):
        return None
    lead = " ".join(body.split()[:120]).casefold()
    dated_actions = [
        list(re.finditer(r"(?:(\d{1,2})월\s*)?(\d{1,2})일", lead[: action.start()]))
        for action in re.finditer("|".join(AGREEMENTS), lead)
    ]
    no_dates: list[re.Match[str]] = []
    dates = next((dates for dates in dated_actions if dates), no_dates)
    if not dates:
        return None
    matched = dates[-1]
    event_clause = lead[matched.start() :]
    completed_milestone = re.search(
        r"(?:계약|납품|인도|진수|발사|승인|완공)(?:을|를)?\s*(?:체결|완료|성공|받았|했다|됐다)",
        event_clause,
    )
    if completed_milestone:
        return None
    month = int(matched[1]) if matched[1] else published.month
    year = published.year - (month > published.month)
    try:
        event_date = date(year, month, int(matched[2]))
    except ValueError:
        return None
    if (published.date() - event_date).days not in range(15):
        return None
    subjects = tuple(
        sorted(
            token.removesuffix("와").removesuffix("과")
            for token in title_tokens(f"{title} {lead}") - GENERIC
            if len(token) >= MIN_SUBJECT_LENGTH and not token.isdigit()
        )
    )
    action_end = next(
        action.end()
        for action in re.finditer("|".join(AGREEMENTS), lead)
        if action.start() >= matched.end()
    )
    party_clause = lead[matched.start() : action_end]
    parties = tuple(
        sorted(
            {
                match[1].casefold()
                for match in re.finditer(
                    r"([가-힣A-Za-z]{3,})(?:\([^)]*\))?(?:와|과)\s", party_clause
                )
            }
        )
    )
    weapons = tuple(
        sorted(entry.identifier for entry in matching_weapons(f"{title} {lead}"))
    )
    return AgreementEvidence(
        event_date=event_date,
        subjects=subjects,
        parties=parties,
        weapons=weapons,
        locations=tuple(
            korean
            for korean, english in AGREEMENT_LOCATIONS
            if korean in party_clause or re.search(rf"\b{english}\b", party_clause)
        ),
    )


def same_agreement(
    left: AgreementEvidence | None, right: AgreementEvidence | None
) -> bool:
    """Require equal occurrence date and several specific shared event anchors."""
    if left is None or right is None or left.event_date != right.event_date:
        return False
    first, second = set(left.subjects), set(right.subjects)
    if (
        (left.weapons and right.weapons and set(left.weapons).isdisjoint(right.weapons))
        or (
            left.locations
            and right.locations
            and set(left.locations).isdisjoint(right.locations)
        )
        or any(party not in second for party in left.parties)
        or any(party not in first for party in right.parties)
    ):
        return False
    shared = first & second
    overlap = len(shared) / max(1, min(len(first), len(second)))
    if not left.parties and not right.parties:
        return (
            len(shared) >= MIN_UNNAMED_SHARED_SUBJECTS
            and overlap >= MIN_UNNAMED_SUBJECT_OVERLAP
        )
    return len(shared) >= MIN_SHARED_SUBJECTS and overlap >= MIN_SUBJECT_OVERLAP
