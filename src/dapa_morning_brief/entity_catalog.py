"""Reviewed aliases; exact identifiers never use edit distance or fuzzy merging."""

import re
from collections.abc import Iterable
from typing import Final

COMPANY_ALIASES: Final[tuple[tuple[str, ...], ...]] = (
    ("한화오션", "한화 오션", "Hanwha Ocean", "대우조선해양", "DSME"),
    ("한화시스템", "한화 시스템", "Hanwha Systems"),
    (
        "LIG D&A",
        "LIG Defense&Aerospace",
        "LIG Defense & Aerospace",
        "LIG 디펜스&에어로스페이스",
        "엘아이지디펜스앤에어로스페이스",
        "LIG넥스원",
        "LIG 넥스원",
        "LIG Nex1",
    ),
    ("현대로템", "현대 로템", "Hyundai Rotem", "ROTEM", "로템"),
    ("한화에어로스페이스", "한화 에어로스페이스", "Hanwha Aerospace"),
    ("한국항공우주", "한국항공우주산업", "Korea Aerospace Industries", "KAI"),
)
AMBIGUOUS_COMPANY_ALIASES: Final[tuple[str, ...]] = ("LIG",)
SOLDIER_SERVICE_ALIASES: Final[tuple[str, ...]] = ("장병이음", "장병e음", "장병이(e)음")
BOUNDARY_SENSITIVE_WEAPON_ALIASES: Final[frozenset[str]] = frozenset(
    {"천궁", "천마", "천무", "비궁", "보라매"},
)


def contains_keyword(text: str, keyword: str) -> bool:
    """Match Latin identifiers at token boundaries while retaining Korean particles."""
    normalized = text.casefold()
    needle = keyword.casefold()
    if needle in BOUNDARY_SENSITIVE_WEAPON_ALIASES:
        return re.search(r"(?<![가-힣])" + re.escape(needle), normalized) is not None
    if re.search(r"[a-z0-9]", needle):
        return (
            re.search(
                r"(?<![a-z0-9-])" + re.escape(needle) + r"(?![a-z0-9-])", normalized
            )
            is not None
        )
    return needle in normalized


def contains_any(text: str, keywords: Iterable[str]) -> bool:
    """Match a reviewed alias without expanding it to similar model numbers."""
    return any(contains_keyword(text, keyword) for keyword in keywords)
