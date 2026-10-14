from datetime import UTC, date, datetime, timedelta

import pytest

from dapa_morning_brief import article_history
from dapa_morning_brief.article_history import ArticleHistory, HistoryEntry
from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.models import Article, Briefing, Section

TODAY = date(2026, 10, 15)
OLD_BODY = (
    "성남시는 지난 8일 브로츠와프에서 폴란드 방산협회와 "
    "사격훈련 시스템 업무협약을 체결했다."
)


def fetch(briefing: Briefing, *, include_government: bool) -> tuple[ArticleBody, ...]:
    assert include_government
    return tuple(
        ArticleBody(item.url, item.title, item.source, OLD_BODY)
        for items in briefing.sections.values()
        for item in items
    )


def test_legacy_agreement_when_hydrated_rejects_rewritten_event() -> None:
    # Given
    entry = HistoryEntry(
        collected_on=TODAY - timedelta(days=1),
        url="example.com/old?",
        title="성남시폴란드자매결연방산협력",
    )
    history = ArticleHistory(entries=(entry,))
    candidate = Article(
        title="성남 방산 수출 교두보 마련",
        url="https://example.com/new",
        published_at=datetime(2026, 10, 14, tzinfo=UTC),
        source="test",
        section=Section.EXPORT_BUSINESS,
    )
    # When
    hydrated = article_history.hydrate_recent_history(
        history, today=TODAY, fetch_bodies=fetch
    )
    # Then
    assert hydrated.entries[0].collected_on == entry.collected_on
    assert (
        hydrated.exclude_recent(
            [candidate],
            today=TODAY,
            bodies=(
                ArticleBody(candidate.url, candidate.title, candidate.source, OLD_BODY),
            ),
        )
        == ()
    )


def unavailable(
    briefing: Briefing, *, include_government: bool
) -> tuple[ArticleBody, ...]:
    assert briefing.sections
    assert include_government
    return ()


def forbidden_fetch(
    briefing: Briefing, *, include_government: bool
) -> tuple[ArticleBody, ...]:
    message = f"Unexpected historical read: {briefing} {include_government}"
    raise AssertionError(message)


def test_unknown_original_body_keeps_legacy_entry_unchanged() -> None:
    # Given
    entry = HistoryEntry(
        collected_on=TODAY - timedelta(days=1),
        url="example.com/old?",
        title="성남시폴란드자매결연",
    )
    history = ArticleHistory(entries=(entry,))
    # When
    result = article_history.hydrate_recent_history(
        history, today=TODAY, fetch_bodies=unavailable
    )
    # Then
    assert result == history


@pytest.mark.parametrize("age", [0, -1, 8])
def test_same_day_future_or_stale_history_is_not_fetched(age: int) -> None:
    # Given
    history = ArticleHistory(
        entries=(
            HistoryEntry(
                collected_on=TODAY - timedelta(days=age),
                url="example.com/old?",
                title="성남시폴란드자매결연",
            ),
        )
    )
    # When
    result = article_history.hydrate_recent_history(
        history, today=TODAY, fetch_bodies=forbidden_fetch
    )
    # Then
    assert result == history


def test_already_hydrated_history_is_not_fetched_again() -> None:
    # Given
    history = ArticleHistory(
        entries=(
            HistoryEntry(
                collected_on=TODAY - timedelta(days=1),
                url="example.com/old?",
                title="성남시폴란드자매결연",
            ),
        )
    )
    hydrated = article_history.hydrate_recent_history(
        history, today=TODAY, fetch_bodies=fetch
    )
    # When
    result = article_history.hydrate_recent_history(
        hydrated, today=TODAY, fetch_bodies=forbidden_fetch
    )
    # Then
    assert result == hydrated


def rejected(
    briefing: Briefing, *, include_government: bool
) -> tuple[ArticleBody, ...]:
    return tuple(
        ArticleBody(body.article_url, body.title, body.source, body.body, "opinion")
        for body in fetch(briefing, include_government=include_government)
    )


def test_rejected_historical_body_is_not_used_as_event_evidence() -> None:
    # Given
    history = ArticleHistory(
        entries=(
            HistoryEntry(
                collected_on=TODAY - timedelta(days=1),
                url="example.com/old?",
                title="성남시폴란드자매결연",
            ),
        )
    )
    # When
    result = article_history.hydrate_recent_history(
        history, today=TODAY, fetch_bodies=rejected
    )
    # Then
    assert result == history


def test_non_agreement_legacy_title_is_not_fetched() -> None:
    # Given
    history = ArticleHistory(
        entries=(
            HistoryEntry(
                collected_on=TODAY - timedelta(days=1),
                url="example.com/old?",
                title="국방장관육군부대대비태세점검",
            ),
        )
    )
    # When
    result = article_history.hydrate_recent_history(
        history, today=TODAY, fetch_bodies=forbidden_fetch
    )
    # Then
    assert result == history
