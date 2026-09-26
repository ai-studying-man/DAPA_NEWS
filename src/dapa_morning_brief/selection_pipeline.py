"""Refill bounded candidate batches after freshness and semantic deduplication."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import chain
from typing import TYPE_CHECKING

from dapa_morning_brief.article_content import fetch_article_bodies
from dapa_morning_brief.article_history import canonical_url
from dapa_morning_brief.briefing import SECTION_ORDER, build_briefing
from dapa_morning_brief.candidate_validation import (
    BODY_DEDUP_CANDIDATE_MULTIPLIER,
    validated_candidates,
)
from dapa_morning_brief.models import Briefing
from dapa_morning_brief.semantic_deduplication import create_semantic_index

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import date

    from dapa_morning_brief.copilot_summary import ArticleBody
    from dapa_morning_brief.models import Article


@dataclass(frozen=True, slots=True)
class SelectionWindow:
    """Freshness and section limits shared by every refill batch."""

    today: date
    max_age_days: int
    max_per_section: int


@dataclass(frozen=True, slots=True)
class SelectionResult:
    """Final selection plus inspected fresh candidates for the history ledger."""

    briefing: Briefing
    articles: tuple[Article, ...]
    bodies: tuple[ArticleBody, ...]


def select_candidates(
    articles: Iterable[Article],
    window: SelectionWindow,
) -> SelectionResult:
    """Inspect bounded batches until represented sections fill or input exhausts."""
    remaining: tuple[Article, ...] = tuple(articles)
    represented = {article.section for article in remaining}
    accepted: list[Article] = []
    bodies: list[ArticleBody] = []
    briefing = build_briefing((), max_per_section=window.max_per_section)
    while remaining and window.max_per_section > 0:
        pool = build_briefing(
            remaining,
            max_per_section=window.max_per_section * BODY_DEDUP_CANDIDATE_MULTIPLIER,
        )
        candidates = tuple(chain.from_iterable(pool.sections.values()))
        attempted = {canonical_url(article.url) for article in candidates}
        remaining = tuple(
            article
            for article in remaining
            if canonical_url(article.url) not in attempted
        )
        fresh = validated_candidates(
            candidates,
            today=window.today,
            max_age_days=window.max_age_days,
            max_per_section=window.max_per_section,
        )
        if not fresh:
            continue
        accepted.extend(fresh)
        batch = Briefing(
            sections={
                section: tuple(
                    article for article in fresh if article.section == section
                )
                for section in SECTION_ORDER
            },
        )
        bodies.extend(fetch_article_bodies(batch, include_government=True))
        index = create_semantic_index(accepted, bodies)
        briefing = build_briefing(
            accepted,
            max_per_section=window.max_per_section,
            article_bodies=bodies,
            semantic_index=index,
        )
        if all(
            len(briefing.sections[section]) >= window.max_per_section
            for section in represented
        ):
            break
    return SelectionResult(briefing, tuple(accepted), tuple(bodies))
