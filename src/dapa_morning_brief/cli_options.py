"""Command-line options shared by preparation and delivery."""

import argparse
from pathlib import Path
from typing import Final

from dapa_morning_brief.models import MAX_ARTICLES_PER_SECTION, MIN_ARTICLES_PER_SECTION

DEFAULT_DAYS: Final = 1
DEFAULT_FALLBACK_DAYS: Final = 5


class BriefNamespace(argparse.Namespace):
    """Typed command-line argument values."""

    days: int = DEFAULT_DAYS
    fallback_days: int = DEFAULT_FALLBACK_DAYS
    max_per_section: int = 5
    include_google: bool = True
    google_only: bool = False
    dry_run: bool = False
    telegram_token: str | None = None
    telegram_chat_id: str | None = None
    prepare_output: Path | None = None
    prepared_input: Path | None = None


def brief_parser() -> argparse.ArgumentParser:
    """Define the existing CLI flags and mutually exclusive delivery modes."""
    parser = argparse.ArgumentParser(
        prog="dapa-morning-brief",
        description="Collect DAPA-related news and send a Telegram morning brief.",
    )
    _ = parser.add_argument(
        "--days", type=int, choices=range(1, 6), default=DEFAULT_DAYS
    )
    _ = parser.add_argument(
        "--fallback-days", type=int, choices=range(1, 6), default=DEFAULT_FALLBACK_DAYS
    )
    _ = parser.add_argument(
        "--max-per-section",
        type=int,
        choices=range(MIN_ARTICLES_PER_SECTION, MAX_ARTICLES_PER_SECTION + 1),
        default=5,
    )
    _ = parser.add_argument("--include-google", action="store_true", default=True)
    _ = parser.add_argument("--google-only", action="store_true")
    _ = parser.add_argument("--dry-run", action="store_true")
    _ = parser.add_argument("--telegram-token")
    _ = parser.add_argument("--telegram-chat-id")
    delivery = parser.add_mutually_exclusive_group()
    _ = delivery.add_argument("--prepare-output", type=Path)
    _ = delivery.add_argument("--prepared-input", type=Path)
    return parser
