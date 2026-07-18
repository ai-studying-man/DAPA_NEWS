from __future__ import annotations

from datetime import UTC, datetime

from dapa_morning_brief.briefing import build_briefing
from dapa_morning_brief.models import Article, Section


def test_build_briefing_prioritizes_explicit_dapa_article() -> None:
    # Given
    published = datetime(2026, 7, 16, tzinfo=UTC)
    general_titles = [
        "국방 획득예산 집행계획 발표",
        "군용기 정비산업 지원방안 공개",
        "방산기업 기술개발 간담회 개최",
    ]
    articles = [
        Article(
            title=title,
            url=f"https://example.com/general-{index}",
            published_at=published,
            source="뉴스",
            section=Section.POLICY,
            feed_rank=index,
        )
        for index, title in enumerate(general_titles)
    ]
    articles.append(
        Article(
            title="방위사업청, 방위력개선사업 계약체결기준 개정",
            url="https://example.com/dapa",
            published_at=published,
            source="뉴스",
            section=Section.POLICY,
            feed_rank=20,
        ),
    )

    # When
    briefing = build_briefing(articles, max_per_section=3)

    # Then
    urls = {article.url for article in briefing.sections[Section.POLICY]}
    assert "https://example.com/dapa" in urls


def test_duplicate_story_keeps_higher_feed_rank_over_agency_priority() -> None:
    # Given
    published = datetime(2026, 7, 16, tzinfo=UTC)
    articles = [
        Article(
            title="방산혁신클러스터 4개 지역 출범",
            url="https://example.com/prominent",
            published_at=published,
            source="뉴스1",
            section=Section.POLICY,
            feed_rank=0,
        ),
        Article(
            title="방위사업청, 방산혁신클러스터 4개 지역 출범",
            url="https://example.com/agency",
            published_at=published,
            source="보도자료",
            section=Section.POLICY,
            feed_rank=20,
        ),
    ]

    # When
    briefing = build_briefing(articles, max_per_section=3)

    # Then
    selected = briefing.sections[Section.POLICY]
    assert [article.url for article in selected] == ["https://example.com/prominent"]


def test_duplicate_story_keeps_higher_view_count_over_agency_priority() -> None:
    published = datetime(2026, 7, 16, tzinfo=UTC)
    articles = [
        Article(
            title="K5 방독면 국방규격 특허 인정",
            url="https://example.com/high-view",
            published_at=published,
            source="뉴스",
            section=Section.POLICY,
            view_count=900,
        ),
        Article(
            title="방위사업청 K5 방독면 국방규격 특허 인정",
            url="https://example.com/agency-low-view",
            published_at=published,
            source="보도자료",
            section=Section.POLICY,
            view_count=100,
        ),
    ]

    briefing = build_briefing(articles, max_per_section=3)

    selected = briefing.sections[Section.POLICY]
    assert [article.url for article in selected] == ["https://example.com/high-view"]


def test_agency_reserve_does_not_replace_known_higher_view_article() -> None:
    published = datetime(2026, 7, 16, tzinfo=UTC)
    titles = [
        "국방 획득예산 집행계획 발표",
        "군용기 정비산업 지원방안 공개",
        "방산기업 기술개발 간담회 개최",
    ]
    articles = [
        Article(
            title=title,
            url=f"https://example.com/popular-{index}",
            published_at=published,
            source="뉴스",
            section=Section.POLICY,
            view_count=3000 - index,
        )
        for index, title in enumerate(titles)
    ]
    articles.append(
        Article(
            title="방위사업청, 제도 개선 설명회 개최",
            url="https://example.com/agency-low-view",
            published_at=published,
            source="보도자료",
            section=Section.POLICY,
            view_count=1,
        ),
    )

    briefing = build_briefing(articles, max_per_section=3)

    urls = {article.url for article in briefing.sections[Section.POLICY]}
    assert "https://example.com/agency-low-view" not in urls


def test_unknown_view_agency_does_not_replace_known_view_article() -> None:
    published = datetime(2026, 7, 16, tzinfo=UTC)
    titles = [
        "국방 획득예산 집행계획 발표",
        "군용기 정비산업 지원방안 공개",
        "방산기업 기술개발 간담회 개최",
    ]
    articles = [
        Article(
            title=title,
            url=f"https://example.com/known-{index}",
            published_at=published,
            source="뉴스",
            section=Section.POLICY,
            view_count=3000 - index * 1000,
        )
        for index, title in enumerate(titles)
    ]
    articles.append(
        Article(
            title="방위사업청, 제도 개선 설명회 개최",
            url="https://example.com/agency-unknown",
            published_at=published,
            source="보도자료",
            section=Section.POLICY,
        ),
    )

    briefing = build_briefing(articles, max_per_section=3)

    urls = {article.url for article in briefing.sections[Section.POLICY]}
    assert "https://example.com/agency-unknown" not in urls
