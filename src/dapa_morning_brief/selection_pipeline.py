"""Inspect additional candidate batches without weakening news quality filters."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import chain
from typing import TYPE_CHECKING, Protocol, final

from typing_extensions import override

from dapa_morning_brief.article_history import canonical_url
from dapa_morning_brief.briefing import build_briefing, build_candidate_pool
from dapa_morning_brief.candidate_validation import (
    BODY_DEDUP_CANDIDATE_MULTIPLIER,
    trace_candidates,
    validated_candidates,
)
from dapa_morning_brief.models import (
    MIN_ARTICLES_PER_SECTION,
    Article,
    Briefing,
    Section,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import date

    from dapa_morning_brief.copilot_summary import ArticleBody


class BodyFetcher(Protocol):
    """The existing article-body inspection boundary."""

    def __call__(
        self, briefing: Briefing, *, include_government: bool
    ) -> tuple[ArticleBody, ...]:
        """Fetch news bodies for a bounded candidate batch."""
        ...


@dataclass(frozen=True, slots=True)
class InsufficientCoverageError(RuntimeError):
    """No valid production brief can be prepared below the category minimum."""

    counts: tuple[tuple[Section, int], ...]

    @override
    def __str__(self) -> str:
        """Expose actual shortages to workflow diagnostics."""
        shortages = " ".join(
            f"{section.value}={count}" for section, count in self.counts
        )
        return (
            f"Insufficient news coverage: {shortages}; "
            f"minimum={MIN_ARTICLES_PER_SECTION}"
        )


@final
class CandidateSelection:
    """Accumulate validated candidates and cached bodies across widening windows."""

    def __init__(self, today: date, limit: int, fetch_bodies: BodyFetcher) -> None:
        """Keep inspected candidates so wider searches cannot discard newer news."""
        self._today = today
        self._limit = limit
        self._fetch_bodies = fetch_bodies
        self._articles: dict[str, Article] = {}
        self._bodies: dict[str, ArticleBody] = {}
        self.briefing = build_briefing((), max_per_section=limit)

    @property
    def bodies(self) -> tuple[ArticleBody, ...]:
        """Return previously fetched bodies without another network request."""
        return tuple(self._bodies.values())

    def inspect(self, articles: Iterable[Article], *, days: int) -> None:
        """Advance beyond rejected or duplicate batches until candidates exhaust."""
        remaining: tuple[Article, ...] = tuple(
            article
            for article in articles
            if canonical_url(article.url) not in self._articles
        )
        while remaining:
            pool = build_candidate_pool(
                remaining,
                max_per_section=self._limit * BODY_DEDUP_CANDIDATE_MULTIPLIER,
            )
            candidates = tuple(chain.from_iterable(pool.sections.values()))
            if not candidates:
                break
            attempted = {canonical_url(article.url) for article in candidates}
            remaining = tuple(
                article
                for article in remaining
                if canonical_url(article.url) not in attempted
            )
            fresh = validated_candidates(
                candidates,
                today=self._today,
                max_age_days=days,
                max_per_section=self._limit,
            )
            trace_candidates("validated", fresh)
            if not fresh:
                continue
            for article in fresh:
                self._articles[canonical_url(article.url)] = article
            batch = Briefing(
                sections={
                    section: tuple(
                        article for article in fresh if article.section == section
                    )
                    for section in Section
                }
            )
            for body in self._fetch_bodies(batch, include_government=True):
                self._bodies[body.article_url] = body
            self.briefing = build_briefing(
                self._articles.values(),
                max_per_section=self._limit,
                article_bodies=self.bodies,
            )
            if all(
                len(self.briefing.sections[section]) >= self._limit
                for section in Section
            ):
                break
