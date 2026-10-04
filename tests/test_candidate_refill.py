from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import TYPE_CHECKING
from unittest.mock import patch

from dapa_morning_brief.cli import main
from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.models import Article, Briefing, Section
from dapa_morning_brief.prepared_brief import PreparedBrief
from dapa_morning_brief.selection_pipeline import CandidateSelection
from tests.coverage_samples import coverage_articles

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


def candidates() -> tuple[Article, ...]:
    seed = coverage_articles()[6]
    return tuple(
        replace(
            seed,
            title=f"장비 확인 기록 {i}"
            if i < 15
            else ("정찰위성 궤도 진입", "잠수함 신규 배치")[i - 15],
            url=f"https://news.test/batch/{i}",
        )
        for i in range(17)
    )


def test_refills_past_first_fifteen_body_duplicates_without_refetching() -> None:
    articles = candidates()
    fetched: list[str] = []
    body = (
        "방위사업청은 전투원용 무전기의 대체 부품 성능 검증 결과를 공개했다. "
        "계약 담당자는 납품 업체가 제출한 시험 자료와 구매 규정을 비교했다. "
        "동등 이상 성능이 확인된 부품의 사용 절차를 검토하고 후속 조치를 결정했다."
    )

    def fetch(
        briefing: Briefing, *, include_government: bool
    ) -> tuple[ArticleBody, ...]:
        assert include_government
        batch = tuple(a for group in briefing.sections.values() for a in group)
        fetched.extend(a.url for a in batch)
        return tuple(
            ArticleBody(a.url, a.title, a.source, body if a in articles[:15] else "")
            for a in batch
        )

    selection = CandidateSelection(date(2026, 10, 4), 5, fetch)
    selection.inspect((*articles, *articles), days=1)
    assert len(selection.briefing.sections[Section.POLICY]) == 3
    assert fetched == [a.url for a in articles]
    selection.inspect(articles, days=2)
    assert fetched == [a.url for a in articles]


def test_rejected_first_batch_does_not_hide_later_fresh_reports() -> None:
    articles = candidates()
    inspected: list[str] = []
    fetched: list[str] = []

    def validate(
        batch: Iterable[Article],
        *,
        today: date,
        max_age_days: int,
        max_per_section: int,
    ) -> tuple[Article, ...]:
        _ = today, max_age_days, max_per_section
        inspected.extend(a.url for a in batch)
        return tuple(a for a in batch if a in articles[15:])

    def fetch(
        briefing: Briefing, *, include_government: bool
    ) -> tuple[ArticleBody, ...]:
        assert include_government
        fetched.extend(a.url for group in briefing.sections.values() for a in group)
        return ()

    selection = CandidateSelection(date(2026, 10, 4), 5, fetch)
    with patch(
        "dapa_morning_brief.selection_pipeline.validated_candidates",
        side_effect=validate,
    ):
        selection.inspect(articles, days=1)
    assert inspected == [a.url for a in articles]
    assert fetched == [a.url for a in articles[15:]]
    assert len(selection.briefing.sections[Section.POLICY]) == 2


def test_backfill_checks_body_reclassification_before_category_filter(
    tmp_path: Path,
) -> None:
    daily = tuple(
        a for a in coverage_articles(3) if a.section != Section.EXPORT_BUSINESS
    )
    titles_and_bodies = (
        ("K9 루마니아 첫 수송대열 공개", "루마니아에 K9 자주포 수출 물량이 인도됐다."),
        ("K2 폴란드 현지 도착", "폴란드에 K2 전차가 수출 계약에 따라 도착했다."),
        (
            "천무 사막 운용 공개",
            "사우디 군의 천무 홍보 영상과 현지 운용 현황을 공개했다.",
        ),
    )
    extra = tuple(
        replace(daily[-1], title=title, url=f"https://news.test/reclassified/{i}")
        for i, (title, _) in enumerate(titles_and_bodies)
    )
    body_by_url = {
        article.url: body
        for article, (_, body) in zip(extra, titles_and_bodies, strict=True)
    }
    collected_days: list[int] = []

    def collect(*, days: int, include_google: bool, only_google: bool) -> list[Article]:
        _ = include_google, only_google
        collected_days.append(days)
        return [*daily, *(extra if days > 1 else ())]

    def fetch(
        briefing: Briefing, *, include_government: bool
    ) -> tuple[ArticleBody, ...]:
        assert include_government
        return tuple(
            ArticleBody(a.url, a.title, a.source, body_by_url.get(a.url, ""))
            for group in briefing.sections.values()
            for a in group
        )

    path = tmp_path / "prepared.json"
    with (
        patch("dapa_morning_brief.cli.collect_articles", side_effect=collect),
        patch("dapa_morning_brief.cli.fetch_article_bodies", side_effect=fetch),
        patch("dapa_morning_brief.cli.collect_weather_forecasts", return_value=()),
        patch("dapa_morning_brief.cli.summarize_article_bodies", return_value=()),
    ):
        assert main(["--prepare-output", str(path)]) == 0
    assert collected_days == [1, 2]
    assert PreparedBrief.load(path).section_counts == (3, 3, 3, 3)
