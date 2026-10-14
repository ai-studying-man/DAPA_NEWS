from datetime import UTC, date, datetime, timedelta

from dapa_morning_brief.article_history import ArticleHistory
from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.models import Article, Briefing, Section
from dapa_morning_brief.selection_pipeline import CandidateSelection


def test_history_exclusion_backfills_after_body_inspection() -> None:
    # Given
    today = date(2026, 10, 15)
    articles = tuple(
        Article(
            title=title,
            url=f"https://example.com/{index}",
            published_at=datetime(2026, 10, 14, 20 - index, tzinfo=UTC),
            source="뉴스",
            section=Section.GOVERNMENT,
        )
        for index, title in enumerate(
            (
                "국방부 병영시설 개선계획 발표",
                "해군 장병 건강검진 확대",
                "공군 조종사 교육 개편",
                "육군 가족지원 프로그램 신설",
            )
        )
    )
    history = ArticleHistory().record(articles[:1], today=today - timedelta(days=1))
    inspected: list[str] = []

    def fetch(
        briefing: Briefing, *, include_government: bool
    ) -> tuple[ArticleBody, ...]:
        assert include_government
        batch = tuple(a for group in briefing.sections.values() for a in group)
        inspected.extend(a.url for a in batch)
        return tuple(
            ArticleBody(article_url=a.url, title=a.title, source=a.source, body=a.title)
            for a in batch
        )

    selection = CandidateSelection(today, 3, fetch)
    # When
    selection.inspect(articles, days=1, history=history)
    # Then
    assert articles[0].url in inspected
    assert selection.briefing.sections[Section.GOVERNMENT] == articles[1:]


def test_empty_history_preserves_existing_selection_interface() -> None:
    # Given
    def fetch(
        briefing: Briefing, *, include_government: bool
    ) -> tuple[ArticleBody, ...]:
        assert include_government
        assert not any(briefing.sections.values())
        return ()

    selection = CandidateSelection(date(2026, 10, 15), 5, fetch)
    # When
    selection.inspect((), days=1)
    # Then
    assert all(not group for group in selection.briefing.sections.values())
