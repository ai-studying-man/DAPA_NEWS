"""Run the DAPA morning briefing collection and delivery command."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime
from io import TextIOWrapper
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Final
from zoneinfo import ZoneInfo

from dapa_morning_brief import official_press_releases
from dapa_morning_brief.article_content import fetch_article_bodies
from dapa_morning_brief.briefing import build_briefing, format_telegram_message
from dapa_morning_brief.collector import collect_articles
from dapa_morning_brief.copilot_summary import summarize_article_bodies
from dapa_morning_brief.models import PRACTICE_POINT_SECTIONS, Section
from dapa_morning_brief.prepared_brief import PreparedBrief
from dapa_morning_brief.telegram import (
    TelegramSendError,
    parse_chat_ids,
    send_telegram_messages,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

DEFAULT_DAYS: Final = 1
DEFAULT_FALLBACK_DAYS: Final = 2
KST: Final[ZoneInfo] = ZoneInfo("Asia/Seoul")
COPILOT_SUMMARY_TEMPLATE: Final = (
    "Copilot summary: generated={generated} fallback={fallback} bodies={bodies}\n"
)
PRESS_RELEASE_CACHE_ENV: Final = "DAPA_PRESS_RELEASE_CACHE"
PREPARED_BRIEF_TEMPLATE: Final = "Prepared brief saved: {path}\n"
BODY_DEDUP_CANDIDATE_MULTIPLIER: Final = 3


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


def main(argv: Sequence[str] | None = None) -> int:
    """Run the DAPA morning brief job."""
    _configure_stdio()
    args = BriefNamespace()
    _ = _parser().parse_args(argv, namespace=args)
    today = datetime.now(KST).date()
    if args.prepared_input is not None:
        return _send_prepared(args, today=today, path=args.prepared_input)

    prepared = _prepare_brief(
        args,
        today=today,
        generate_practice_points=not args.dry_run,
    )
    if args.prepare_output is not None:
        prepared.save(args.prepare_output)
        _ = sys.stderr.write(
            PREPARED_BRIEF_TEMPLATE.format(path=args.prepare_output),
        )
        return 0
    if args.dry_run:
        _ = sys.stdout.write(f"{prepared.message}\n")
        return 0
    return _send_text(args, prepared.message)


def _prepare_brief(
    args: BriefNamespace,
    *,
    today: date,
    generate_practice_points: bool,
) -> PreparedBrief:
    days = args.days
    max_per_section = args.max_per_section
    articles = collect_articles(
        days=days,
        include_google=args.include_google,
        only_google=args.google_only,
    )
    missing_sections = set(Section).difference(article.section for article in articles)
    if missing_sections and args.fallback_days > days:
        fallback_articles = collect_articles(
            days=args.fallback_days,
            include_google=True,
            only_google=False,
        )
        articles.extend(
            article
            for article in fallback_articles
            if article.section in missing_sections
        )

    article_bodies = ()
    if generate_practice_points:
        candidate_briefing = build_briefing(
            articles,
            max_per_section=max_per_section * BODY_DEDUP_CANDIDATE_MULTIPLIER,
        )
        article_bodies = fetch_article_bodies(candidate_briefing)
        candidate_articles = tuple(
            chain.from_iterable(candidate_briefing.sections.values()),
        )
        briefing = build_briefing(
            candidate_articles,
            max_per_section=max_per_section,
            article_bodies=article_bodies,
        )
    else:
        briefing = build_briefing(articles, max_per_section=max_per_section)
    raw_cache_path = os.getenv(PRESS_RELEASE_CACHE_ENV, "")
    latest_press_releases = official_press_releases.collect_latest_press_releases(
        as_of=today,
        cache_path=Path(raw_cache_path) if raw_cache_path else None,
    )
    practice_points = ()
    selected_count = sum(
        len(briefing.sections[section]) for section in PRACTICE_POINT_SECTIONS
    )
    if generate_practice_points:
        selected_urls = {
            article.url
            for section in PRACTICE_POINT_SECTIONS
            for article in briefing.sections[section]
        }
        selected_bodies = tuple(
            body for body in article_bodies if body.article_url in selected_urls
        )
        practice_points = summarize_article_bodies(selected_bodies)
        _ = sys.stderr.write(
            COPILOT_SUMMARY_TEMPLATE.format(
                generated=len(practice_points),
                fallback=selected_count - len(practice_points),
                bodies=len(selected_bodies),
            ),
        )
    message = format_telegram_message(
        briefing,
        today=today,
        practice_points=practice_points,
        official_press_releases=latest_press_releases,
    )
    return PreparedBrief(
        briefing_date=today,
        message=message,
        generated_practice_points=len(practice_points),
        fallback_practice_points=(
            selected_count - len(practice_points) if generate_practice_points else 0
        ),
    )


def _send_prepared(args: BriefNamespace, *, today: date, path: Path) -> int:
    prepared = PreparedBrief.load(path)
    if prepared.briefing_date != today:
        _ = sys.stderr.write(
            f"Prepared brief date mismatch: {prepared.briefing_date} != {today}.\n",
        )
        return 2
    if args.dry_run:
        _ = sys.stdout.write(f"{prepared.message}\n")
        return 0
    return _send_text(args, prepared.message)


def _send_text(args: BriefNamespace, message: str) -> int:
    token = args.telegram_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
    raw_chat_ids = (
        args.telegram_chat_id
        or os.getenv("TELEGRAM_CHAT_IDS", "")
        or os.getenv("TELEGRAM_CHAT_ID", "")
    )
    chat_ids = parse_chat_ids(raw_chat_ids)
    if not token or not chat_ids:
        _ = sys.stderr.write(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required.\n",
        )
        return 2

    try:
        send_telegram_messages(token=token, chat_ids=chat_ids, text=message)
    except TelegramSendError as error:
        _ = sys.stderr.write(f"{error}\n")
        return 1
    return 0


def _parser() -> argparse.ArgumentParser:
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


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, TextIOWrapper):
            stream.reconfigure(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
