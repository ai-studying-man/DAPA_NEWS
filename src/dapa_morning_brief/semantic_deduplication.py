"""Conservative, pairwise semantic comparison of news reports on CPU."""

from __future__ import annotations

import logging
import math
import os
import re
import sys
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

from httpx import HTTPError
from typing_extensions import override

from dapa_morning_brief.semantic_embeddings import encode as _encode

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from dapa_morning_brief.copilot_summary import ArticleBody
    from dapa_morning_brief.models import Article

_LOGGER: Final = logging.getLogger(__name__)
_MIN_CONTENT: Final = 120
_MIN_ARTICLES: Final = 2
_TITLE_THRESHOLD: Final = 0.94
_CONTENT_TITLE_THRESHOLD: Final = 0.85
_STRONG_CONTENT_THRESHOLD: Final = 0.96
_STRONG_CONTENT_TITLE_THRESHOLD: Final = 0.82
_COUNTRIES: Final = (
    "폴란드",
    "루마니아",
    "노르웨이",
    "핀란드",
    "에스토니아",
    "호주",
    "인도",
    "인도네시아",
    "필리핀",
    "말레이시아",
    "태국",
    "베트남",
    "사우디",
    "아랍에미리트",
    "UAE",
    "이집트",
    "튀르키예",
    "이라크",
    "미국",
    "캐나다",
    "영국",
    "프랑스",
    "독일",
    "페루",
    "칠레",
)
_WEAPON: Final = re.compile(
    r"\b(?:K\s?-?\s?\d+[A-Z\d]*|KF\s?-?\s?21|FA\s?-?\s?50)\b|천무|천궁|레드백",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class SemanticThresholdError(ValueError):
    """Invalid operator-provided semantic threshold."""

    value: str

    @override
    def __str__(self) -> str:
        """Describe the invalid operator setting."""
        return (
            "DAPA_SEMANTIC_THRESHOLD must be finite and between 0 and 1: "
            f"{self.value!r}"
        )


@dataclass(frozen=True, slots=True)
class _ArticleVectors:
    title: tuple[float, ...]
    content: tuple[float, ...]
    has_content: bool


@dataclass(frozen=True, slots=True)
class SemanticIndex:
    """Immutable vectors; compare each candidate directly to its representative."""

    vectors: Mapping[str, _ArticleVectors]
    threshold: float

    @property
    def scored_articles(self) -> int:
        """Return the number of articles successfully embedded."""
        return len(self.vectors)

    @property
    def content_articles(self) -> int:
        """Return how many embeddings have substantive body or description text."""
        return sum(vector.has_content for vector in self.vectors.values())

    def are_same(self, left: Article, right: Article) -> bool:
        """Require corroborating title similarity and reject conflicting facts."""
        if ("인터뷰" in left.title) != ("인터뷰" in right.title):
            return False
        first, second = self.vectors.get(left.url), self.vectors.get(right.url)
        if (
            first is None
            or second is None
            or conflicting_story_facts(left.title, right.title)
        ):
            return False
        title_score = sum(a * b for a, b in zip(first.title, second.title, strict=True))
        if first.has_content and second.has_content:
            content_score = sum(
                a * b for a, b in zip(first.content, second.content, strict=True)
            )
            duplicate = (
                title_score >= _CONTENT_TITLE_THRESHOLD
                and content_score >= self.threshold
            ) or (
                title_score >= _STRONG_CONTENT_TITLE_THRESHOLD
                and content_score >= max(self.threshold, _STRONG_CONTENT_THRESHOLD)
            )
        else:
            content_score = None
            duplicate = title_score >= _TITLE_THRESHOLD
        if duplicate:
            print(  # noqa: T201 - operational duplicate decision
                f"Semantic duplicate: title_score={title_score:.3f}",
                f"content_score={content_score}",
                f"left={left.title!r} right={right.title!r}",
                file=sys.stderr,
            )
        return duplicate


def conflicting_story_facts(left: str, right: str) -> bool:
    """Reject explicit opposing outcomes or different weapon export destinations."""
    positive = ("체결", "서명", "성사")
    negative = ("취소", "철회", "무산", "파기")
    if (
        any(term in left for term in positive)
        and any(term in right for term in negative)
    ) or (
        any(term in right for term in positive)
        and any(term in left for term in negative)
    ):
        return True
    left_weapons = {
        re.sub(r"[\s-]", "", match.group().upper()) for match in _WEAPON.finditer(left)
    }
    right_weapons = {
        re.sub(r"[\s-]", "", match.group().upper()) for match in _WEAPON.finditer(right)
    }
    if left_weapons and right_weapons and left_weapons.isdisjoint(right_weapons):
        return True
    left_countries = _countries(left)
    right_countries = _countries(right)
    return bool(
        left_weapons & right_weapons
        and left_countries
        and right_countries
        and left_countries.isdisjoint(right_countries)
    )


def _countries(title: str) -> set[str]:
    # Longest country wins; India requires a target construction, not delivery wording.
    countries: set[str] = set()
    remaining = title
    for country in sorted(_COUNTRIES, key=len, reverse=True):
        if country == "인도":
            found = re.search(
                r"인도(?:에|와|향|군|가|는|의|로)|인도\s+(?:수출|수입|정부|육군|해군|공군)",
                remaining,
            )
            if found:
                countries.add(country)
        elif country in remaining:
            countries.add(country)
            remaining = remaining.replace(country, " ")
    return countries


def create_semantic_index(
    articles: Iterable[Article], article_bodies: Iterable[ArticleBody]
) -> SemanticIndex:
    """Encode once per run; retain lexical matching if model loading fails."""
    raw_threshold = os.getenv("DAPA_SEMANTIC_THRESHOLD", "0.93")
    try:
        threshold = float(raw_threshold)
    except ValueError as error:
        raise SemanticThresholdError(raw_threshold) from error
    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise SemanticThresholdError(raw_threshold)
    items = tuple({article.url: article for article in articles}.values())
    empty = SemanticIndex(MappingProxyType({}), threshold)
    if len(items) < _MIN_ARTICLES:
        return empty
    bodies = {body.article_url: body.body.strip() for body in article_bodies}
    contents = tuple(
        bodies.get(article.url) or article.description.strip() for article in items
    )
    texts = tuple(
        text
        for article, content in zip(items, contents, strict=True)
        for text in (
            f"query: {article.title}",
            f"query: {article.title} {content[:1000]}",
        )
    )
    try:
        raw_vectors = _encode(texts)
        vectors = tuple(
            tuple(value / norm for value in vector)
            for vector in raw_vectors
            for norm in (math.sqrt(sum(component * component for component in vector)),)
        )
        if (
            len({len(vector) for vector in vectors}) != 1
            or len(vectors) != len(texts)
            or any(
                not vector or not all(math.isfinite(value) for value in vector)
                for vector in vectors
            )
        ):
            _LOGGER.warning(
                "Semantic deduplication unavailable: invalid embedding output"
            )
            return empty
    except (
        ImportError,
        OSError,
        RuntimeError,
        ValueError,
        ZeroDivisionError,
        HTTPError,
    ) as error:
        _LOGGER.warning(
            "Semantic deduplication unavailable; lexical matching retained: %s", error
        )
        return empty
    indexed = {
        article.url: _ArticleVectors(
            vectors[2 * i], vectors[2 * i + 1], len(contents[i]) >= _MIN_CONTENT
        )
        for i, article in enumerate(items)
    }
    result = SemanticIndex(MappingProxyType(indexed), threshold)
    print(  # noqa: T201 - operational CLI diagnostics belong on stderr
        f"Semantic deduplication: scored={result.scored_articles}",
        f"content={result.content_articles} threshold={threshold:.3f}",
        file=sys.stderr,
    )
    return result
