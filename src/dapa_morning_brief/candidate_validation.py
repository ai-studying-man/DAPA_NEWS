"""Validate candidate freshness before final selection."""

from __future__ import annotations

import sys
from itertools import chain
from typing import TYPE_CHECKING, Final

from dapa_morning_brief.article_content import filter_articles_by_publisher_date
from dapa_morning_brief.briefing import build_briefing

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import date

    from dapa_morning_brief.models import Article

BODY_DEDUP_CANDIDATE_MULTIPLIER: Final = 3
REJECTION_TEMPLATE: Final = "Freshness excluded: publisher_date={date} title={title}\n"
FRESHNESS_SUMMARY_TEMPLATE: Final = (
    "Publisher freshness ({days}d): checked={checked} accepted={accepted} "
    "stale={stale} unverifiable={unverifiable}\n"
)


def validated_candidates(
    articles: Iterable[Article],
    *,
    today: date,
    max_age_days: int,
    max_per_section: int,
) -> tuple[Article, ...]:
    """Deduplicate bounded candidates and verify original publication dates."""
    candidate_briefing = build_briefing(
        tuple(articles),
        max_per_section=max_per_section * BODY_DEDUP_CANDIDATE_MULTIPLIER,
    )
    candidates = tuple(chain.from_iterable(candidate_briefing.sections.values()))
    freshness = filter_articles_by_publisher_date(
        candidates,
        as_of=today,
        max_age_days=max_age_days,
    )
    if freshness.checked_search:
        accepted = (
            freshness.checked_search - len(freshness.rejected) - freshness.unverifiable
        )
        _ = sys.stderr.write(
            FRESHNESS_SUMMARY_TEMPLATE.format(
                days=max_age_days,
                checked=freshness.checked_search,
                accepted=accepted,
                stale=len(freshness.rejected),
                unverifiable=freshness.unverifiable,
            ),
        )
        for rejection in freshness.rejected:
            _ = sys.stderr.write(
                REJECTION_TEMPLATE.format(
                    date=rejection.publisher_date.isoformat(),
                    title=rejection.title,
                ),
            )
        for title in freshness.unverified_titles:
            _ = sys.stderr.write(
                f"Freshness excluded: publisher_date=unverifiable title={title}\n",
            )
    return freshness.articles
