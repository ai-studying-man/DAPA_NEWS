from __future__ import annotations

from datetime import UTC, datetime
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

import pytest

from dapa_morning_brief.cli import DEFAULT_DAYS, DEFAULT_FALLBACK_DAYS, KST, main
from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.models import (
    Article,
    PracticePoint,
    Section,
    WeatherForecast,
)


class CliTest(TestCase):
    def test_cli_collects_weather_for_the_briefing_date(self) -> None:
        # Given
        output = StringIO()
        weather = (
            WeatherForecast(
                city="과천시",
                condition="맑음",
                minimum_celsius=21.0,
                maximum_celsius=31.0,
            ),
        )

        # When
        with (
            patch("dapa_morning_brief.cli.collect_articles", return_value=[]),
            patch(
                "dapa_morning_brief.cli.collect_weather_forecasts",
                return_value=weather,
            ) as collect,
            patch("sys.stdout", output),
        ):
            exit_code = main(["--dry-run"])

        # Then
        assert exit_code == 0
        assert collect.call_args.kwargs["as_of"] == datetime.now(KST).date()
        assert "1. 과천시 : 맑음 / 21℃ ~ 31℃" in output.getvalue()

    def test_cli_defaults_to_daily_freshness_window(self) -> None:
        # Given
        daily_window_days = 1
        fallback_window_days = 2

        # When
        configured_days = DEFAULT_DAYS
        configured_fallback_days = DEFAULT_FALLBACK_DAYS

        # Then
        assert configured_days == daily_window_days
        assert configured_fallback_days == fallback_window_days

    def test_cli_backfills_sections_missing_from_daily_collection(self) -> None:
        published = datetime(2026, 7, 16, tzinfo=UTC)
        daily_policy = Article(
            title="방위사업청 일일 정책 기사",
            url="https://example.com/daily-policy",
            published_at=published,
            source="뉴스",
            section=Section.POLICY,
        )
        fallback_government = Article(
            title="이 대통령 주재 국무회의 주요 안건 의결",
            url="https://example.com/government",
            published_at=published,
            source="뉴스",
            section=Section.GOVERNMENT,
        )
        fallback_policy = Article(
            title="이틀 전 방위사업청 정책 기사",
            url="https://example.com/old-policy",
            published_at=published,
            source="뉴스",
            section=Section.POLICY,
        )

        output = StringIO()
        with (
            patch(
                "dapa_morning_brief.cli.collect_articles",
                side_effect=[
                    [daily_policy],
                    [fallback_government, fallback_policy],
                ],
            ) as collect,
            patch(
                "dapa_morning_brief.cli.collect_weather_forecasts",
                return_value=(),
            ),
            patch("sys.stdout", output),
        ):
            exit_code = main(["--dry-run", "--days", "1", "--fallback-days", "2"])

        assert exit_code == 0
        assert collect.call_count == 2
        assert daily_policy.title in output.getvalue()
        assert fallback_government.title in output.getvalue()
        assert fallback_policy.title not in output.getvalue()

    def test_cli_allows_five_articles_per_section(self) -> None:
        output = StringIO()
        with (
            patch("dapa_morning_brief.cli.collect_articles", return_value=[]),
            patch(
                "dapa_morning_brief.cli.collect_weather_forecasts",
                return_value=(),
            ),
            patch("sys.stdout", output),
        ):
            exit_code = main(["--dry-run", "--max-per-section", "5"])

        assert exit_code == 0

    def test_cli_rejects_more_than_five_articles_per_section(self) -> None:
        with pytest.raises(SystemExit) as raised:
            _ = main(["--dry-run", "--max-per-section", "6"])

        assert raised.value.code == 2

    def test_cli_sends_copilot_practice_point_when_available(self) -> None:
        # Given
        article = Article(
            title="KF-21 후속 양산 일정 확정",
            url="https://example.com/kf21",
            published_at=datetime(2026, 8, 6, tzinfo=UTC),
            source="테스트뉴스",
            section=Section.WEAPON_SYSTEM,
        )
        generated = PracticePoint(
            article_url=article.url,
            text="후속 양산 계약 시점과 납품 일정을 확인할 필요가 있음.",
        )
        article_body = ArticleBody(
            article_url=article.url,
            title=article.title,
            source=article.source,
            body="후속 양산 계약과 납품 일정이 발표됐다.",
        )
        diagnostic_output = StringIO()

        # When
        with (
            patch("dapa_morning_brief.cli.collect_articles", return_value=[article]),
            patch(
                "dapa_morning_brief.cli.collect_weather_forecasts",
                return_value=(),
            ),
            patch(
                "dapa_morning_brief.cli.fetch_article_bodies",
                return_value=(article_body,),
            ),
            patch(
                "dapa_morning_brief.cli.summarize_article_bodies",
                return_value=(generated,),
            ),
            patch("dapa_morning_brief.cli.send_telegram_messages") as send,
            patch("sys.stderr", diagnostic_output),
        ):
            exit_code = main(
                ["--telegram-token", "token", "--telegram-chat-id", "1234"],
            )

        # Then
        assert exit_code == 0
        assert generated.text in send.call_args.kwargs["text"]
        assert (
            diagnostic_output.getvalue()
            == "Copilot summary: generated=1 fallback=0 bodies=1\n"
        )

    def test_cli_omits_press_releases_from_dry_run(self) -> None:
        # Given
        output = StringIO()

        # When
        with (
            patch("dapa_morning_brief.cli.collect_articles", return_value=[]),
            patch(
                "dapa_morning_brief.cli.collect_weather_forecasts",
                return_value=(),
            ),
            patch("sys.stdout", output),
        ):
            exit_code = main(["--dry-run"])

        # Then
        assert exit_code == 0
        assert "보도자료" not in output.getvalue()
