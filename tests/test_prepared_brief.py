from __future__ import annotations

from datetime import UTC, date, datetime
from io import StringIO
from typing import TYPE_CHECKING
from unittest.mock import patch

from dapa_morning_brief.cli import KST, main
from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.models import Article, PracticePoint, Section
from dapa_morning_brief.prepared_brief import PreparedBrief

if TYPE_CHECKING:
    from pathlib import Path


def test_prepared_brief_round_trips_only_delivery_data(tmp_path: Path) -> None:
    # Given
    path = tmp_path / "prepared-brief.json"
    prepared = PreparedBrief(
        briefing_date=date(2026, 8, 8),
        message="prepared telegram message",
        generated_practice_points=12,
        fallback_practice_points=3,
    )

    # When
    prepared.save(path)
    loaded = PreparedBrief.load(path)

    # Then
    assert loaded == prepared
    assert "article_body" not in path.read_text(encoding="utf-8")


def test_cli_prepares_json_without_sending_telegram(tmp_path: Path) -> None:
    # Given
    article = Article(
        title="KF-21 후속 양산 일정 확정",
        url="https://example.com/kf21",
        published_at=datetime(2026, 8, 7, tzinfo=UTC),
        source="테스트뉴스",
        section=Section.WEAPON_SYSTEM,
    )
    body = ArticleBody(
        article_url=article.url,
        title=article.title,
        source=article.source,
        body="이 문장은 준비 JSON에 저장되면 안 되는 원문 기사 본문입니다.",
    )
    point = PracticePoint(
        article_url=article.url,
        text="후속양산 계약 시점과 납품 일정 확인",
    )
    output_path = tmp_path / "prepared.json"

    # When
    with (
        patch("dapa_morning_brief.cli.collect_articles", return_value=[article]),
        patch(
            "dapa_morning_brief.official_press_releases.collect_latest_press_releases",
            return_value=(),
        ),
        patch("dapa_morning_brief.cli.fetch_article_bodies", return_value=(body,)),
        patch(
            "dapa_morning_brief.cli.summarize_article_bodies",
            return_value=(point,),
        ),
        patch("dapa_morning_brief.cli.send_telegram_messages") as send,
    ):
        exit_code = main(["--prepare-output", str(output_path)])
    prepared = PreparedBrief.load(output_path)

    # Then
    assert exit_code == 0
    assert point.text in prepared.message
    assert body.body not in output_path.read_text(encoding="utf-8")
    send.assert_not_called()


def test_cli_sends_prepared_json_without_collecting_again(tmp_path: Path) -> None:
    # Given
    input_path = tmp_path / "prepared.json"
    prepared = PreparedBrief(
        briefing_date=datetime.now(KST).date(),
        message="already prepared telegram message",
        generated_practice_points=1,
        fallback_practice_points=0,
    )
    prepared.save(input_path)

    # When
    with (
        patch("dapa_morning_brief.cli.collect_articles") as collect,
        patch("dapa_morning_brief.cli.send_telegram_messages") as send,
    ):
        exit_code = main(
            [
                "--prepared-input",
                str(input_path),
                "--telegram-token",
                "token",
                "--telegram-chat-id",
                "1234",
            ],
        )

    # Then
    assert exit_code == 0
    collect.assert_not_called()
    assert send.call_args.kwargs["text"] == prepared.message


def test_cli_dry_runs_prepared_json_without_telegram(tmp_path: Path) -> None:
    # Given
    input_path = tmp_path / "prepared.json"
    prepared = PreparedBrief(
        briefing_date=datetime.now(KST).date(),
        message="already prepared telegram message",
        generated_practice_points=1,
        fallback_practice_points=0,
    )
    prepared.save(input_path)
    output = StringIO()

    # When
    with (
        patch("dapa_morning_brief.cli.send_telegram_messages") as send,
        patch("sys.stdout", output),
    ):
        exit_code = main(["--prepared-input", str(input_path), "--dry-run"])

    # Then
    assert exit_code == 0
    assert output.getvalue() == f"{prepared.message}\n"
    send.assert_not_called()
