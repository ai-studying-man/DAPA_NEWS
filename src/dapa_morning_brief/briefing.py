"""Build and render a deduplicated DAPA morning briefing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from dapa_morning_brief.models import Article, Briefing, Section
from dapa_morning_brief.sources import AGENCY_KEYWORDS
from dapa_morning_brief.story_deduplication import are_same_articles
from dapa_morning_brief.telegram_format import daily_quote, format_telegram_message

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = ["build_briefing", "daily_quote", "format_telegram_message"]

SECTION_ORDER: Final[tuple[Section, ...]] = (
    Section.GOVERNMENT,
    Section.POLICY,
    Section.WEAPON_SYSTEM,
    Section.EXPORT_BUSINESS,
)

SOURCE_PRIORITY: Final[tuple[str, ...]] = (
    "정책브리핑",
    "방위사업청",
    "국방부",
    "국방일보",
    "뉴스와이어",
    "네이버",
    "Google",
)


def build_briefing(
    articles: Iterable[Article],
    *,
    max_per_section: int,
) -> Briefing:
    """Select newest non-duplicate articles for each section."""
    buckets: dict[Section, list[Article]] = {section: [] for section in SECTION_ORDER}
    selected_articles: list[Article] = []

    for section in SECTION_ORDER:
        candidates = sorted(
            (article for article in articles if article.section == section),
            key=_article_rank,
        )
        for article in candidates:
            if any(
                are_same_articles(article, selected) for selected in selected_articles
            ):
                continue
            buckets[section].append(article)
            selected_articles.append(article)
            if len(buckets[section]) >= max_per_section:
                break
        _reserve_agency_article(
            section_articles=buckets[section],
            candidates=candidates,
            selected_articles=selected_articles,
        )

    return Briefing(
        sections={section: tuple(buckets[section]) for section in SECTION_ORDER},
    )


def _source_rank(source: str) -> int:
    for index, keyword in enumerate(SOURCE_PRIORITY):
        if keyword in source:
            return index
    return len(SOURCE_PRIORITY)


def _article_rank(article: Article) -> tuple[int, int, int, int, int, float]:
    view_count_known = 0 if article.view_count is not None else 1
    view_count_rank = -(article.view_count if article.view_count is not None else 0)
    feed_rank_known = 0 if article.feed_rank is not None else 1
    feed_rank = article.feed_rank if article.feed_rank is not None else 0
    return (
        view_count_known,
        view_count_rank,
        feed_rank_known,
        feed_rank,
        _source_rank(article.source),
        -article.published_at.timestamp(),
    )


def _reserve_agency_article(
    *,
    section_articles: list[Article],
    candidates: list[Article],
    selected_articles: list[Article],
) -> None:
    if not section_articles or any(
        _is_agency_article(item) for item in section_articles
    ):
        return
    for candidate in candidates:
        if not _is_agency_article(candidate):
            continue
        if any(
            are_same_articles(candidate, selected) for selected in selected_articles
        ):
            continue
        replaced = section_articles[-1]
        if replaced.view_count is not None and (
            candidate.view_count is None or candidate.view_count < replaced.view_count
        ):
            continue
        section_articles[-1] = candidate
        selected_articles.remove(replaced)
        selected_articles.append(candidate)
        return


def _is_agency_article(article: Article) -> bool:
    metadata = f"{article.title} {article.description} {article.source}".casefold()
    return any(keyword.casefold() in metadata for keyword in AGENCY_KEYWORDS)
