"""Run the DAPA morning briefing collection and delivery command."""

from __future__ import annotations

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
from dapa_morning_brief.briefing import (
    format_telegram_message,
)
from dapa_morning_brief.candidate_validation import (
    trace_candidates,
)
from dapa_morning_brief.cli_options import (
    DEFAULT_DAYS,
    DEFAULT_FALLBACK_DAYS,
    BriefNamespace,
)
from dapa_morning_brief.cli_options import (
    brief_parser as _parser,
)
from dapa_morning_brief.collector import collect_articles
from dapa_morning_brief.copilot_summary import summarize_article_bodies
from dapa_morning_brief.models import (
    MIN_ARTICLES_PER_SECTION,
    PRACTICE_POINT_SECTIONS,
    Section,
)
from dapa_morning_brief.prepared_brief import PreparedBrief
from dapa_morning_brief.selection_pipeline import (
    CandidateSelection,
    InsufficientCoverageError,
)
from dapa_morning_brief.telegram import (
    TelegramSendError,
    parse_chat_ids,
    send_telegram_messages,
)
from dapa_morning_brief.weather import collect_weather_forecasts

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["DEFAULT_DAYS", "DEFAULT_FALLBACK_DAYS", "BriefNamespace", "main"]

KST: Final[ZoneInfo] = ZoneInfo("Asia/Seoul")
COPILOT_SUMMARY_TEMPLATE: Final = (
    "Copilot summary: generated={generated} fallback={fallback} bodies={bodies}\n"
)
PREPARED_BRIEF_TEMPLATE: Final = "Prepared brief saved: {path}\n"
SELECTED_TEMPLATE: Final = (
    "Selected: section={section} count={count} below_minimum={below}\n"
)


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
        return 0 if prepared.has_minimum_coverage else 3
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
    selection = CandidateSelection(today, max_per_section, fetch_article_bodies)
    for window_days in range(days, max(days, args.fallback_days) + 1):
        missing_sections = {
            section
            for section in Section
            if len(selection.briefing.sections[section]) < MIN_ARTICLES_PER_SECTION
        }
        if not missing_sections:
            break
        initial = window_days == days
        if not initial:
            logging.getLogger(__name__).warning(
                "news_backfill days=%d missing_sections=%s",
                window_days,
                ",".join(sorted(s.value for s in missing_sections)),
            )
        candidates = collect_articles(
            days=window_days,
            include_google=args.include_google if initial else True,
            only_google=args.google_only if initial else False,
        )
        trace_candidates("collected" if initial else "fallback_collected", candidates)
        selection.inspect(
            history.exclude_recent(candidates, today=today),
            days=window_days,
        )
    briefing = selection.briefing
    article_bodies = selection.bodies
    trace_candidates("selected", chain.from_iterable(briefing.sections.values()))
    for section in Section:
        count = len(briefing.sections[section])
        _ = sys.stderr.write(
            SELECTED_TEMPLATE.format(
                section=section.value,
                count=count,
                below=count < MIN_ARTICLES_PER_SECTION,
            ),
        )
    if not any(briefing.sections.values()) and not args.dry_run:
        message = "No validated news remains; refusing an empty Telegram brief."
        raise RuntimeError(message)
    shortages = tuple(
        (section, len(briefing.sections[section]))
        for section in Section
        if len(briefing.sections[section]) < MIN_ARTICLES_PER_SECTION
    )
    if shortages and not args.dry_run:
        raise InsufficientCoverageError(shortages)
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
        section_counts=(
            len(briefing.sections[Section.GOVERNMENT]),
            len(briefing.sections[Section.POLICY]),
            len(briefing.sections[Section.WEAPON_SYSTEM]),
            len(briefing.sections[Section.EXPORT_BUSINESS]),
        ),
        message=message,
        generated_practice_points=len(practice_points),
        fallback_practice_points=(
            selected_count - len(practice_points) if generate_practice_points else 0
        ),
    )
    if history_path is not None and not args.dry_run:
        history.record(
            chain.from_iterable(briefing.sections.values()), today=today
        ).save(
            history_path,
        )
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
        return 0 if prepared.has_minimum_coverage else 3
    if not prepared.has_minimum_coverage:
        _ = sys.stderr.write("Prepared brief has a category below minimum=3.\n")
        return 3
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


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, TextIOWrapper):
            stream.reconfigure(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
