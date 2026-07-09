from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Final

from dapa_morning_brief.briefing import build_briefing, format_telegram_message
from dapa_morning_brief.collector import collect_articles
from dapa_morning_brief.telegram import (
    TelegramSendError,
    parse_chat_ids,
    send_telegram_messages,
)

DEFAULT_DAYS: Final = 1
DEFAULT_FALLBACK_DAYS: Final = 2


def main(argv: Sequence[str] | None = None) -> int:
    """Run the DAPA morning brief job."""
    _configure_stdio()
    args = _parser().parse_args(argv)
    days = int(args.days)
    max_per_section = int(args.max_per_section)
    articles = collect_articles(
        days=days,
        include_google=bool(args.include_google),
        only_google=bool(args.google_only),
    )
    if not articles and int(args.fallback_days) > days:
        articles = collect_articles(
            days=int(args.fallback_days),
            include_google=True,
            only_google=False,
        )

    briefing = build_briefing(articles, max_per_section=max_per_section)
    message = format_telegram_message(
        briefing,
        today=datetime.now(UTC).astimezone().date(),
    )

    if bool(args.dry_run):
        sys.stdout.write(f"{message}\n")
        return 0

    token = args.telegram_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
    raw_chat_ids = (
        args.telegram_chat_id
        or os.getenv("TELEGRAM_CHAT_IDS", "")
        or os.getenv("TELEGRAM_CHAT_ID", "")
    )
    chat_ids = parse_chat_ids(raw_chat_ids)
    if not token or not chat_ids:
        sys.stderr.write("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required.\n")
        return 2

    try:
        send_telegram_messages(token=token, chat_ids=chat_ids, text=message)
    except TelegramSendError as error:
        sys.stderr.write(f"{error}\n")
        return 1
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dapa-morning-brief",
        description="Collect DAPA-related news and send a Telegram morning brief.",
    )
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--fallback-days", type=int, default=DEFAULT_FALLBACK_DAYS)
    parser.add_argument("--max-per-section", type=int, default=3)
    parser.add_argument("--include-google", action="store_true", default=True)
    parser.add_argument("--google-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--telegram-token")
    parser.add_argument("--telegram-chat-id")
    return parser


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
