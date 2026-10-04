from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from dapa_morning_brief import cli
from dapa_morning_brief.article_history import ArticleHistory, canonical_url
from dapa_morning_brief.models import Section
from dapa_morning_brief.prepared_brief import PreparedBrief
from tests.coverage_samples import coverage_articles

if TYPE_CHECKING:
    from pathlib import Path

    from dapa_morning_brief.models import Article


def test_expands_until_every_category_has_three_to_five_unique_reports(
    tmp_path: Path,
) -> None:
    articles = coverage_articles()
    daily = (
        tuple(a for a in articles if a.section != Section.POLICY)
        + tuple(a for a in articles if a.section == Section.POLICY)[:1]
    )
    calls: list[int] = []

    def collect(*, days: int, include_google: bool, only_google: bool) -> list[Article]:
        _ = include_google, only_google
        calls.append(days)
        extra = tuple(a for a in articles if a.section == Section.POLICY)[:days]
        return [*daily, *extra, *daily]

    with (
        patch("dapa_morning_brief.cli.collect_articles", side_effect=collect),
        patch("dapa_morning_brief.cli.fetch_article_bodies", return_value=()),
        patch("dapa_morning_brief.cli.collect_weather_forecasts", return_value=()),
    ):
        prepared = prepare_news(tmp_path)
    assert calls == [1, 2, 3]
    for section in Section:
        selected = [
            a for a in articles if a.section == section and a.url in prepared.message
        ]
        assert 3 <= len(selected) <= 5, section.value
        assert len({a.url for a in selected}) == len(selected)


def test_insufficient_production_cannot_save_send_or_record_history(
    tmp_path: Path,
) -> None:
    articles = tuple(a for a in coverage_articles() if a.section != Section.POLICY)
    output = tmp_path / "prepared.json"
    history = tmp_path / "history.json"
    with (
        patch.dict("os.environ", {"DAPA_HISTORY_PATH": str(history)}),
        patch(
            "dapa_morning_brief.cli.collect_articles", return_value=articles
        ) as collect,
        patch("dapa_morning_brief.cli.fetch_article_bodies", return_value=()),
        patch("dapa_morning_brief.cli.summarize_article_bodies") as summarize,
        patch("dapa_morning_brief.cli.send_telegram_messages") as send,
        pytest.raises(RuntimeError, match=r"policy=0.*minimum=3"),
    ):
        _ = cli.main(["--prepare-output", str(output)])
    assert [call.kwargs["days"] for call in collect.call_args_list] == [1, 2, 3, 4, 5]
    assert not output.exists()
    assert not history.exists()
    summarize.assert_not_called()
    send.assert_not_called()


def test_duplicate_and_opinion_padding_cannot_meet_minimum(tmp_path: Path) -> None:
    samples = coverage_articles()
    report = next(a for a in samples if a.section == Section.POLICY)
    articles = (
        *(a for a in samples if a.section != Section.POLICY),
        report,
        replace(report, url="https://news.test/other-publisher"),
        replace(
            report,
            title="[사설] 방위사업청 개혁이 필요하다",
            url="https://news.test/opinion",
        ),
        replace(report, title="[웹툰] 조달 작전 12화", url="https://news.test/webtoon"),
    )
    with (
        patch("dapa_morning_brief.cli.collect_articles", return_value=articles),
        patch("dapa_morning_brief.cli.fetch_article_bodies", return_value=()),
        pytest.raises(RuntimeError, match=r"policy=1.*minimum=3"),
    ):
        _ = prepare_news(tmp_path)


@pytest.mark.parametrize("limit", [3, 4, 5])
def test_final_counts_obey_requested_limit_after_all_filters(
    limit: int, tmp_path: Path
) -> None:
    with (
        patch(
            "dapa_morning_brief.cli.collect_articles", return_value=coverage_articles()
        ) as collect,
        patch("dapa_morning_brief.cli.fetch_article_bodies", return_value=()),
        patch("dapa_morning_brief.cli.collect_weather_forecasts", return_value=()),
    ):
        prepared = prepare_news(tmp_path, limit=limit)
    assert prepared.section_counts == (limit, limit, limit, limit)
    assert prepared.has_minimum_coverage
    assert collect.call_count == 1


def test_records_only_final_selected_news_not_unused_candidates(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    articles = coverage_articles()
    with (
        patch.dict("os.environ", {"DAPA_HISTORY_PATH": str(path)}),
        patch("dapa_morning_brief.cli.collect_articles", return_value=articles),
        patch("dapa_morning_brief.cli.fetch_article_bodies", return_value=()),
        patch("dapa_morning_brief.cli.collect_weather_forecasts", return_value=()),
    ):
        prepared = prepare_news(tmp_path)
    entries = ArticleHistory.load(path).entries
    assert len(entries) == 20
    for article in articles:
        assert any(entry.url == canonical_url(article.url) for entry in entries) == (
            article.url in prepared.message
        )


def test_five_day_search_is_attempted_before_rejecting_one_report(
    tmp_path: Path,
) -> None:
    samples = coverage_articles()
    policies = tuple(a for a in samples if a.section == Section.POLICY)
    other = tuple(a for a in samples if a.section != Section.POLICY)
    calls: list[int] = []

    def collect(*, days: int, include_google: bool, only_google: bool) -> list[Article]:
        _ = include_google, only_google
        calls.append(days)
        return [*other, *(policies[:3] if days == 5 else policies[:1])]

    with (
        patch("dapa_morning_brief.cli.collect_articles", side_effect=collect),
        patch("dapa_morning_brief.cli.fetch_article_bodies", return_value=()),
        patch("dapa_morning_brief.cli.collect_weather_forecasts", return_value=()),
    ):
        prepared = prepare_news(tmp_path)
    assert calls == [1, 2, 3, 4, 5]
    assert prepared.section_counts == (5, 3, 5, 5)


def prepare_news(tmp_path: Path, *, limit: int = 5) -> PreparedBrief:
    path = tmp_path / "prepared.json"
    with patch("dapa_morning_brief.cli.summarize_article_bodies", return_value=()):
        assert (
            cli.main(["--prepare-output", str(path), "--max-per-section", str(limit)])
            == 0
        )
    return PreparedBrief.load(path)
