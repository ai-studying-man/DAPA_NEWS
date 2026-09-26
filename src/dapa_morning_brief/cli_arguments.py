"""Command-line options for collection and prepared delivery."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Final

DEFAULT_DAYS: Final = 1
DEFAULT_FALLBACK_DAYS: Final = 2


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
    """Build the shared collection and delivery argument parser."""
    parser = argparse.ArgumentParser(
        prog="dapa-morning-brief",
        description="Collect DAPA-related news and send a Telegram morning brief.",
    )
    _ = parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    _ = parser.add_argument(
        "--fallback-days",
        type=int,
        default=DEFAULT_FALLBACK_DAYS,
    )
    _ = parser.add_argument(
        "--max-per-section",
        type=int,
        choices=range(1, 6),
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
