"""Run the DAPA morning briefing collection and delivery command."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, datetime
from io import TextIOWrapper
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Final
from zoneinfo import ZoneInfo

from dapa_morning_brief.article_content import (
    fetch_article_bodies,
)
from dapa_morning_brief.article_history import ArticleHistory
from dapa_morning_brief.briefing import build_briefing, format_telegram_message
from dapa_morning_brief.candidate_validation import (
    BODY_DEDUP_CANDIDATE_MULTIPLIER,
    validated_candidates,
)
from dapa_morning_brief.collector import collect_articles
from dapa_morning_brief.copilot_summary import summarize_article_bodies
from dapa_morning_brief.models import PRACTICE_POINT_SECTIONS, Section
from dapa_morning_brief.prepared_brief import PreparedBrief
from dapa_morning_brief.telegram import (
    TelegramSendError,
    parse_chat_ids,
    send_telegram_messages,
)
from dapa_morning_brief.weather import collect_weather_forecasts

if TYPE_CHECKING:
    from collections.abc import Sequence

DEFAULT_DAYS: Final = 1
DEFAULT_FALLBACK_DAYS: Final = 2
KST: Final[ZoneInfo] = ZoneInfo("Asia/Seoul")
COPILOT_SUMMARY_TEMPLATE: Final = (
    "Copilot summary: generated={generated} fallback={fallback} bodies={bodies}\n"
)
PREPARED_BRIEF_TEMPLATE: Final = "Prepared brief saved: {path}\n"
SELECTED_TEMPLATE: Final = (
    "Selected: section={section} count={count} below_minimum={below}\n"
)


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
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
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
    raw_path = os.getenv("DAPA_HISTORY_PATH")
    history_path = Path(raw_path) if raw_path else None
    history = ArticleHistory.load(history_path) if history_path else ArticleHistory()
    days = args.days
    max_per_section = args.max_per_section
    articles = collect_articles(
        days=days,
        include_google=args.include_google,
        only_google=args.google_only,
    )
    articles = list(
        validated_candidates(
            history.exclude_recent(articles, today=today),
            today=today,
            max_age_days=days,
            max_per_section=max_per_section,
        ),
    )
    collected_articles = tuple(articles)
    candidate_briefing = build_briefing(
        articles,
        max_per_section=max_per_section * BODY_DEDUP_CANDIDATE_MULTIPLIER,
    )
    candidate_articles = tuple(
        chain.from_iterable(candidate_briefing.sections.values()),
    )
    article_bodies = ()
    if generate_practice_points:
        article_bodies = fetch_article_bodies(
            candidate_briefing, include_government=True
        )
        briefing = build_briefing(
            candidate_articles,
            max_per_section=max_per_section,
            article_bodies=article_bodies,
        )
    else:
        briefing = build_briefing(candidate_articles, max_per_section=max_per_section)
    missing_sections = {
        section
        for section in Section
        if len(briefing.sections[section]) < min(3, max_per_section)
    }
    if missing_sections and args.fallback_days > days:
        fallback_articles = collect_articles(
            days=args.fallback_days,
            include_google=True,
            only_google=False,
        )
        validated_fallback = validated_candidates(
            (
                article
                for article in history.exclude_recent(fallback_articles, today=today)
                if article.section in missing_sections
            ),
            today=today,
            max_age_days=args.fallback_days,
            max_per_section=max_per_section,
        )
        collected_articles += validated_fallback
        articles.extend(validated_fallback)
        candidate_briefing = build_briefing(
            articles,
            max_per_section=max_per_section * BODY_DEDUP_CANDIDATE_MULTIPLIER,
            article_bodies=article_bodies,
        )
        if generate_practice_points:
            article_bodies = fetch_article_bodies(
                candidate_briefing, include_government=True
            )
        briefing = build_briefing(
            tuple(chain.from_iterable(candidate_briefing.sections.values())),
            max_per_section=max_per_section,
            article_bodies=article_bodies,
        )
    for section in Section:
        count = len(briefing.sections[section])
        _ = sys.stderr.write(
            SELECTED_TEMPLATE.format(
                section=section.value,
                count=count,
                below=count < min(3, max_per_section),
            ),
        )
    if not any(briefing.sections.values()) and not args.dry_run:
        message = "No validated news remains; refusing an empty Telegram brief."
        raise RuntimeError(message)
    weather_forecasts = collect_weather_forecasts(as_of=today)
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
        weather_forecasts=weather_forecasts,
    )
    prepared = PreparedBrief(
        briefing_date=today,
        message=message,
        generated_practice_points=len(practice_points),
        fallback_practice_points=(
            selected_count - len(practice_points) if generate_practice_points else 0
        ),
    )
    if history_path is not None and not args.dry_run:
        history.record(collected_articles, today=today).save(history_path)
    return prepared


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
