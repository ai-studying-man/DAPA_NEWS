from __future__ import annotations

from unittest import TestCase

from dapa_morning_brief.cli import DEFAULT_DAYS, DEFAULT_FALLBACK_DAYS


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
