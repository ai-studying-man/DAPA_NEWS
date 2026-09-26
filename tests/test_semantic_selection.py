from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from dapa_morning_brief.briefing import build_briefing
from dapa_morning_brief.models import Article, Section
from dapa_morning_brief.semantic_deduplication import create_semantic_index

if TYPE_CHECKING:
    import pytest


def test_semantic_duplicates_across_sections_leave_room_for_distinct_news(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    articles = (
        Article(
            "대통령 경제 협력 회담 결과 발표",
            "https://example.com/a",
            datetime(2026, 9, 26, tzinfo=UTC),
            "A",
            Section.GOVERNMENT,
        ),
        Article(
            "양국 투자 보호 합의와 공동행동계획 채택",
            "https://example.com/b",
            datetime(2026, 9, 26, tzinfo=UTC),
            "B",
            Section.EXPORT_BUSINESS,
        ),
        Article(
            "신형 잠수함 시험 항해 시작",
            "https://example.com/c",
            datetime(2026, 9, 26, tzinfo=UTC),
            "C",
            Section.EXPORT_BUSINESS,
        ),
    )

    def encode(_texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return ((1.0, 0.0), (1.0, 0.0), (1.0, 0.0), (1.0, 0.0), (0.0, 1.0), (0.0, 1.0))

    monkeypatch.setattr("dapa_morning_brief.semantic_deduplication._encode", encode)
    index = create_semantic_index(articles, ())
    legacy = build_briefing(articles, max_per_section=1)
    result = build_briefing(articles, max_per_section=1, semantic_index=index)
    assert legacy.sections[Section.EXPORT_BUSINESS] == (articles[1],)
    assert result.sections[Section.EXPORT_BUSINESS] == (articles[2],)
    assert result.sections[Section.GOVERNMENT] == (articles[0],)


def test_model_failure_preserves_lexical_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    articles = tuple(
        Article(
            title,
            f"https://example.com/{i}",
            datetime(2026, 9, 26, tzinfo=UTC),
            "news",
            Section.POLICY,
        )
        for i, title in enumerate(("국방 예산 심의", "군수품 공급 계약"))
    )

    def fail(_texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        msg = "model download unavailable"
        raise OSError(msg)

    monkeypatch.setattr("dapa_morning_brief.semantic_deduplication._encode", fail)
    index = create_semantic_index(articles, ())
    assert index.scored_articles == 0
    assert build_briefing(articles, max_per_section=5, semantic_index=index) == (
        build_briefing(articles, max_per_section=5)
    )


def test_same_url_remains_one_article_when_headline_outcome_changes() -> None:
    articles = tuple(
        Article(
            title,
            "https://example.com/report",
            datetime(2026, 9, 26, tzinfo=UTC),
            "news",
            Section.EXPORT_BUSINESS,
        )
        for title in ("K9 수출 계약 체결", "K9 수출 계약 취소")
    )
    assert (
        len(
            build_briefing(articles, max_per_section=5).sections[
                Section.EXPORT_BUSINESS
            ]
        )
        == 1
    )


def test_conflicting_outcomes_survive_identical_description() -> None:
    articles = tuple(
        Article(
            title,
            f"https://example.com/{i}",
            datetime(2026, 9, 26, tzinfo=UTC),
            "news",
            Section.EXPORT_BUSINESS,
            description="폴란드 정부와 한국 방산 기업의 장기 공급 계약 협상 배경 설명",
        )
        for i, title in enumerate(("K9 수출 계약 체결", "K9 수출 계약 취소"))
    )
    assert (
        len(
            build_briefing(articles, max_per_section=5).sections[
                Section.EXPORT_BUSINESS
            ]
        )
        == 2
    )
