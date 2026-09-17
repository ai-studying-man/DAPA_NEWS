from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from dapa_morning_brief.article_history import ArticleHistory
from dapa_morning_brief.briefing import build_briefing
from dapa_morning_brief.cli import KST, main
from dapa_morning_brief.models import Article, Section
from dapa_morning_brief.story_deduplication import are_same_story

if TYPE_CHECKING:
    from pathlib import Path


def test_newest_article_wins_over_older_high_view_count() -> None:
    older = Article(
        "조달 제도 개선",
        "https://example.com/old",
        datetime(2026, 9, 16, tzinfo=UTC),
        "방위사업청",
        Section.POLICY,
        view_count=10000,
    )
    newest = Article(
        "획득 예산 확정",
        "https://example.com/new",
        datetime(2026, 9, 17, tzinfo=UTC),
        "다른 매체",
        Section.POLICY,
    )
    result = build_briefing(iter([older, newest]), max_per_section=1)
    assert result.sections[Section.POLICY] == (newest,)


def test_empty_production_brief_cannot_send_or_save(tmp_path: Path) -> None:
    path = tmp_path / "brief.json"
    with (
        patch("dapa_morning_brief.cli.collect_articles", return_value=[]),
        patch("dapa_morning_brief.cli.fetch_article_bodies", return_value=()),
        patch("dapa_morning_brief.cli.send_telegram_messages") as send,
        pytest.raises(RuntimeError, match="No validated news"),
    ):
        _ = main(["--prepare-output", str(path)])
    send.assert_not_called()
    assert not path.exists()


def test_preparation_excludes_prior_collected_article_and_persists_new(
    tmp_path: Path,
) -> None:
    today = datetime.now(KST).date()
    prior = Article(
        "조달 규정 발표",
        "https://example.com/prior",
        datetime.now(UTC),
        "test",
        Section.POLICY,
    )
    fresh = Article(
        "신규 전투기 배치",
        "https://example.com/fresh",
        datetime.now(UTC),
        "test",
        Section.WEAPON_SYSTEM,
    )
    path = tmp_path / "history.json"
    ArticleHistory().record([prior], today=today - timedelta(days=1)).save(path)
    brief_path = tmp_path / "brief.json"
    with (
        patch.dict(os.environ, {"DAPA_HISTORY_PATH": str(path)}),
        patch("dapa_morning_brief.cli.collect_articles", return_value=[prior, fresh]),
        patch("dapa_morning_brief.cli.fetch_article_bodies", return_value=()),
        patch("dapa_morning_brief.cli.collect_weather_forecasts", return_value=()),
        patch("dapa_morning_brief.cli.summarize_article_bodies", return_value=()),
    ):
        assert main(["--prepare-output", str(brief_path)]) == 0
    rendered = brief_path.read_text(encoding="utf-8")
    assert prior.url not in rendered
    assert fresh.url in rendered
    assert len(ArticleHistory.load(path).entries) == 2
    before = path.read_bytes()
    with (
        patch.dict(os.environ, {"DAPA_HISTORY_PATH": str(path)}),
        patch("dapa_morning_brief.cli.collect_articles", return_value=[fresh]),
        patch("dapa_morning_brief.cli.collect_weather_forecasts", return_value=()),
    ):
        assert main(["--dry-run"]) == 0
    assert path.read_bytes() == before


def test_drone_demonstration_incident_wording_is_one_story() -> None:

    assert are_same_story(
        "국방부 주최 시연 행사서 무인기 잇따라 추락",
        "국방부 주관 무인기 시연행사서 첨단드론 추락 속출 원인 조사",
    )
