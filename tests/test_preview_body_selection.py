from datetime import UTC, datetime
from io import StringIO
from unittest.mock import patch

import pytest

from dapa_morning_brief.cli import main
from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.models import Article, Section


def test_dry_run_deduplicates_bodies_without_summarizing_or_sending(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # Given
    articles = [
        Article(
            title,
            f"https://example.com/{index}",
            datetime.now(UTC),
            "뉴스",
            Section.POLICY,
        )
        for index, title in enumerate(("무전기 대체 부품 검증", "계약 변경 절차 점검"))
    ]
    body = (
        "방위사업청은 전투원용 무전기의 대체 부품 성능 검증 결과를 공개했다. "
        "계약 담당자는 납품 업체가 제출한 시험 자료와 구매 규정을 비교했다. "
        "동등 이상 성능이 확인된 부품의 사용 절차를 검토하고 후속 조치를 결정했다."
    )
    bodies = tuple(
        ArticleBody(article_url=a.url, title=a.title, source=a.source, body=body)
        for a in articles
    )
    output = StringIO()
    monkeypatch.setenv("DAPA_NEWS_TRACE", "1")
    # When
    with (
        patch("dapa_morning_brief.cli.collect_articles", return_value=articles),
        patch("dapa_morning_brief.cli.fetch_article_bodies", return_value=bodies),
        patch("dapa_morning_brief.cli.collect_weather_forecasts", return_value=()),
        patch("dapa_morning_brief.cli.summarize_article_bodies") as summarize,
        patch("dapa_morning_brief.cli.send_telegram_messages") as send,
        patch("sys.stdout", output),
    ):
        result = main(["--dry-run", "--fallback-days", "1"])
    # Then
    assert result == 3
    assert sum(a.url in output.getvalue() for a in articles) == 1
    summarize.assert_not_called()
    send.assert_not_called()
    assert "stage=collected" in caplog.text
    assert "stage=selected" in caplog.text
    assert body not in caplog.text
