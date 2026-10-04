"""Identify appointment lead events by their named appointee and office."""

from __future__ import annotations

import re
from typing import Final

_ROLE: Final = r"(?:[가-힣]{2,8})(?:특별보좌관|특보|위원장)"
_ROLE_FIRST: Final = re.compile(
    "".join(
        (
            rf"(?P<role>{_ROLE})(?:에|으로|로|된)?\s*",
            r"(?:(?:\d+선|\d+성|장군|출신|신임)\s*)*",
            r"(?P<person>[가-힣]{2,4})(?=\s|[·,….]|$)",
        )
    )
)
_PERSON_FIRST: Final = re.compile(
    "".join(
        (
            r"(?P<person>[가-힣]{2,4})\s+(?:의원\s+)?(?:대통령\s+)?",
            rf"(?P<role>{_ROLE})",
        )
    )
)
_APPOINTMENT: Final = re.compile(r"위촉|임명|인선|선임|특보된|특보 된|특별보좌관된")
_OTHER_ACTION: Final = re.compile(
    r"방문|연설|발언|논쟁|해임|철회|사퇴|취소|거부|과거|지난해|작년|비교|분석|평가|논평|인터뷰|대담|토론|칼럼|사설"
)


def _title_offices(title: str) -> frozenset[tuple[str, str]]:
    title = re.sub(
        r"([가-힣]{2,8})\s+(특별보좌관|특보|위원장)",
        lambda match: match[1] + match[2],
        title,
    )
    offices: set[tuple[str, str]] = set()
    for pattern in (_ROLE_FIRST, _PERSON_FIRST):
        for match in pattern.finditer(title):
            role = match["role"].removeprefix("대통령").replace("특별보좌관", "특보")
            person = match["person"]
            if person not in {"위촉", "임명", "해임", "선임", "의원", "대통령"}:
                offices.add((role, person))
    return frozenset(offices)


def compare_appointment_leads(
    left_title: str, right_title: str, left_lead: str, right_lead: str
) -> bool | None:
    """Return a decision only when both headlines name a person and office."""
    left_offices, right_offices = (
        _title_offices(left_title),
        _title_offices(right_title),
    )
    if not left_offices or not right_offices:
        return None
    if _OTHER_ACTION.search(left_title) or _OTHER_ACTION.search(right_title):
        return False
    shared_roles = {role for role, _ in left_offices} & {
        role for role, _ in right_offices
    }
    conflicting_people = any(
        {person for office, person in left_offices if office == role}.isdisjoint(
            person for office, person in right_offices if office == role
        )
        for role in shared_roles
    )
    if left_offices.isdisjoint(right_offices) or conflicting_people:
        return False
    for title, lead in ((left_title, left_lead), (right_title, right_lead)):
        title_offices = _title_offices(title)
        office_listing = len(title_offices) > 1 and bool(re.search(r"[…·,]", title))
        if _APPOINTMENT.search(title) or office_listing:
            continue
        first_sentence = re.split(r"[.!?\n]", lead, maxsplit=1)[0]
        if (
            not _APPOINTMENT.search(first_sentence)
            or _OTHER_ACTION.search(first_sentence)
            or not _title_offices(first_sentence) & _title_offices(title)
        ):
            return False
    return True
