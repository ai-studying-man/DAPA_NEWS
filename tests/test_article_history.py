from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from dapa_morning_brief.article_history import ArticleHistory
from dapa_morning_brief.models import Article, Section

if TYPE_CHECKING:
    from pathlib import Path

TODAY = date(2026, 9, 17)


def article(
    url: str = "https://example.com/1", title: str = "방사청 사업 착수"
) -> Article:
    return Article(
        title=title,
        url=url,
        published_at=datetime(2026, 9, 17, tzinfo=UTC),
        source="test",
        section=Section.POLICY,
    )


@pytest.mark.parametrize(
    ("age", "excluded"), [(0, False), (1, True), (2, True), (3, False)]
)
def test_only_previous_two_collection_days_are_excluded(
    age: int, *, excluded: bool
) -> None:
    item = article()
    history = ArticleHistory().record([item], today=TODAY - timedelta(days=age))
    assert (history.exclude_recent([item], today=TODAY) == ()) is excluded


def test_tracking_and_syndicated_titles_are_excluded_but_new_event_survives() -> None:
    history = ArticleHistory().record([article()], today=TODAY - timedelta(days=1))
    tracking = article(url="http://example.com/1?utm_source=naver", title="새 표제")
    syndicated = article(url="https://other.example/2", title="방사청: 사업 착수!")
    followup = article(url="https://example.com/3", title="방사청 사업 계약 체결")
    assert history.exclude_recent([tracking, syndicated, followup], today=TODAY) == (
        followup,
    )


def test_history_round_trip_preserves_first_collection_date(tmp_path: Path) -> None:
    yesterday = TODAY - timedelta(days=1)
    history = ArticleHistory().record([article()], today=yesterday)
    updated = history.record([article()], today=TODAY)
    path = tmp_path / "history.json"
    updated.save(path)
    assert ArticleHistory.load(path).entries[0].collected_on == yesterday
    assert "body" not in path.read_text(encoding="utf-8")


def test_corrupt_history_is_not_silently_ignored(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    _ = path.write_text("broken", encoding="utf-8")
    with pytest.raises(ValidationError):
        _ = ArticleHistory.load(path)


def test_recollected_identity_starts_a_new_exclusion_window() -> None:
    history = ArticleHistory().record([article()], today=TODAY - timedelta(days=3))
    history = history.record([article()], today=TODAY)
    assert history.exclude_recent([article()], today=TODAY + timedelta(days=1)) == ()
