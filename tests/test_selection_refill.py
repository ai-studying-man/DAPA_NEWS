"""Regression coverage for selection after semantic collapse and stale batches."""

from collections.abc import Iterable
from datetime import UTC, date, datetime

import pytest

from dapa_morning_brief import selection_pipeline as pipeline
from dapa_morning_brief import semantic_deduplication as semantic
from dapa_morning_brief.briefing import build_briefing
from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.models import Article, Briefing, Section


def articles() -> tuple[Article, ...]:
    titles = (
        "해외 고객 확보한 포병 장비",
        "유럽 땅으로 향하는 국산 화력",
        "우리 기술로 만든 곡사포 공급",
        "현지 군대 선택받은 방산 제품",
        "대규모 구매 결정에 생산 확대",
        "장거리 타격 플랫폼 판매 성과",
        "동맹국 전력 증강 돕는 납품",
        "글로벌 시장 개척한 중공업",
        "신규 주문으로 공장 가동 활발",
        "양국 협력 결실 맺은 수주",
        "자주포 도입 계획 최종 승인",
        "육군 현대화 이끄는 교역",
        "화포 도입 사업 본격 추진",
        "외국 정부 조달 문턱 넘었다",
        "수출길 열린 지상 전투 차량",
        "우주 정찰 위성 발사 성공",
    )
    return tuple(
        Article(
            title,
            f"https://news.test/{i}",
            datetime(2026, 9, 26, tzinfo=UTC),
            "news",
            Section.POLICY,
            feed_rank=i,
        )
        for i, title in enumerate(titles)
    )


def accept(
    items: Iterable[Article],
    *,
    today: date,
    max_age_days: int,
    max_per_section: int,
) -> tuple[Article, ...]:
    _ = today, max_age_days, max_per_section
    return tuple(items)


def vectors(texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
    return tuple((0.0, 1.0) if "위성" in text else (1.0, 0.0) for text in texts)


def test_refills_after_fifteen_reports_collapse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given a real lexical pool that fills before the sixteenth distinct event.
    items = articles()
    assert len(build_briefing(items, max_per_section=15).sections[Section.POLICY]) == 15
    fetched: list[str] = []

    def fetch(
        briefing: Briefing, *, include_government: bool
    ) -> tuple[ArticleBody, ...]:
        assert include_government
        batch = tuple(a for group in briefing.sections.values() for a in group)
        fetched.extend(a.url for a in batch)
        return tuple(ArticleBody(a.url, a.title, a.source, "") for a in batch)

    monkeypatch.setattr(pipeline, "validated_candidates", accept)
    monkeypatch.setattr(pipeline, "fetch_article_bodies", fetch)
    monkeypatch.setattr(semantic, "_encode", vectors)
    # When semantic comparison collapses the first batch.
    result = pipeline.select_candidates(
        items + items, pipeline.SelectionWindow(date(2026, 9, 26), 2, 5)
    )
    # Then refill includes the later distinct event without duplicate fetches.
    assert result.briefing.sections[Section.POLICY] == (items[0], items[-1])
    assert len(result.articles) == 16
    assert len(fetched) == len(set(fetched)) == 16


def test_rejected_batch_advances_to_fresh_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given freshness rejects every candidate in the first bounded pool.
    items = articles()
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
        candidates = tuple(batch)
        inspected.extend(a.url for a in candidates)
        return tuple(a for a in candidates if a.url == items[-1].url)

    def fetch(
        briefing: Briefing, *, include_government: bool
    ) -> tuple[ArticleBody, ...]:
        assert include_government
        fetched.extend(a.url for group in briefing.sections.values() for a in group)
        return ()

    monkeypatch.setattr(pipeline, "validated_candidates", validate)
    monkeypatch.setattr(pipeline, "fetch_article_bodies", fetch)
    # When selecting with a rejected first batch.
    result = pipeline.select_candidates(
        items, pipeline.SelectionWindow(date(2026, 9, 26), 2, 5)
    )
    # Then rejection still progresses and only the fresh candidate is fetched.
    assert result.articles == (items[-1],)
    assert len(inspected) == len(set(inspected)) == 16
    assert fetched == [items[-1].url]


def test_empty_input_does_not_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given no collected articles.
    fetched: list[Briefing] = []

    def fetch(
        briefing: Briefing, *, include_government: bool
    ) -> tuple[ArticleBody, ...]:
        _ = include_government
        fetched.append(briefing)
        return ()

    monkeypatch.setattr(pipeline, "fetch_article_bodies", fetch)
    # When selecting an empty collection.
    result = pipeline.select_candidates(
        (), pipeline.SelectionWindow(date(2026, 9, 26), 2, 5)
    )
    # Then no network work is requested and all sections are empty.
    assert not fetched
    assert not result.articles
    assert not any(result.briefing.sections.values())


def test_semantic_duplicates_stay_global_across_refill_batches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given a government report and policy paraphrases of that same event.
    items = articles()
    government = Article(
        "국방 협력 결실 알린 정부 발표",
        "https://news.test/government",
        items[0].published_at,
        "news",
        Section.GOVERNMENT,
    )

    def fetch(
        briefing: Briefing,
        *,
        include_government: bool,
    ) -> tuple[ArticleBody, ...]:
        _ = briefing
        assert include_government
        return ()

    monkeypatch.setattr(pipeline, "validated_candidates", accept)
    monkeypatch.setattr(pipeline, "fetch_article_bodies", fetch)
    monkeypatch.setattr(semantic, "_encode", vectors)
    # When refill compares each new batch against accumulated sections.
    result = pipeline.select_candidates(
        (government, *items),
        pipeline.SelectionWindow(date(2026, 9, 26), 2, 5),
    )
    # Then the first section owns the shared event and policy keeps the unique event.
    assert result.briefing.sections[Section.GOVERNMENT] == (government,)
    assert result.briefing.sections[Section.POLICY] == (items[-1],)


def test_stops_when_represented_section_is_full(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given one represented section and a limit of one.
    items = articles()
    fetched: list[str] = []

    def fetch(
        briefing: Briefing,
        *,
        include_government: bool,
    ) -> tuple[ArticleBody, ...]:
        assert include_government
        fetched.extend(a.url for group in briefing.sections.values() for a in group)
        return ()

    monkeypatch.setattr(pipeline, "validated_candidates", accept)
    monkeypatch.setattr(pipeline, "fetch_article_bodies", fetch)
    monkeypatch.setattr(semantic, "_encode", vectors)
    # When the first bounded batch already fills the requested section.
    result = pipeline.select_candidates(
        items,
        pipeline.SelectionWindow(date(2026, 9, 26), 2, 1),
    )
    # Then later articles never incur body fetch work.
    assert result.briefing.sections[Section.POLICY] == (items[0],)
    assert len(fetched) == 3
