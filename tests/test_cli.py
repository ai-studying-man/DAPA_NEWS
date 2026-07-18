from __future__ import annotations

from datetime import UTC, datetime
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

import pytest

from dapa_morning_brief.cli import DEFAULT_DAYS, DEFAULT_FALLBACK_DAYS, main
from dapa_morning_brief.models import Article, Section


class CliTest(TestCase):
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
            patch("sys.stdout", output),
        ):
            exit_code = main(["--dry-run", "--max-per-section", "5"])

        assert exit_code == 0

    def test_cli_rejects_more_than_five_articles_per_section(self) -> None:
        with pytest.raises(SystemExit) as raised:
            _ = main(["--dry-run", "--max-per-section", "6"])

        assert raised.value.code == 2
