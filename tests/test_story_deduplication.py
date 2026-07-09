from __future__ import annotations

from datetime import UTC, datetime

from dapa_morning_brief.briefing import build_briefing
from dapa_morning_brief.models import Article, Section


def test_build_briefing_collapses_july_ten_cross_publisher_duplicates() -> None:
    # Given
    published = datetime(2026, 7, 10, 6, 0, tzinfo=UTC)
    award = "대통령 표창"
    researcher = "김상경 SNT다이내믹스 수석연구원"
    vessel = "무인수상정"
    vessel_leadership = "해양무인체계 독자기술 리더십 확보"
    articles = [
        _article(
            f"{researcher}, K방산 발전 유공 '{award}' - 파이낸셜뉴스",
            "파이낸셜뉴스",
            Section.GOVERNMENT,
            published,
        ),
        _article(
            f"독일 의존 깨고 K2 전차 변속기 국산화…SNT 김상경 이사 {award} - 국민일보",
            "국민일보",
            Section.GOVERNMENT,
            published,
        ),
        _article(
            "K-방산 핵심부품 국산화 이끈 연구원에 대통령 표창 - 매일경제",
            "매일경제",
            Section.GOVERNMENT,
            published,
        ),
        _article(
            f"한화시스템, 30톤급 {vessel} 진수…AI기술 융합 - 네이트",
            "네이트",
            Section.POLICY,
            published,
        ),
        _article(
            f"한화시스템, {vessel_leadership} '30톤급 {vessel}' 전격 진수 - 씨원뉴스",
            "씨원뉴스",
            Section.POLICY,
            published,
        ),
        _article(
            f"한화시스템, {vessel} 진수…해양무인체계 시장 공략 - 뉴스저널리즘",
            "뉴스저널리즘",
            Section.POLICY,
            published,
        ),
    ]

    # When
    briefing = build_briefing(articles, max_per_section=3)

    # Then
    assert len(briefing.sections[Section.GOVERNMENT]) == 1
    assert len(briefing.sections[Section.POLICY]) == 1


def test_build_briefing_keeps_distinct_events_with_same_weapon_name() -> None:
    # Given
    published = datetime(2026, 7, 10, 6, 0, tzinfo=UTC)
    articles = [
        _article(
            "K2 전차 폴란드 2차 수출 계약 체결",
            "국방일보",
            Section.EXPORT_BUSINESS,
            published,
        ),
        _article(
            "K2 전차 국산 변속기 내구도 시험 완료",
            "방위사업청",
            Section.WEAPON_SYSTEM,
            published,
        ),
    ]

    # When
    briefing = build_briefing(articles, max_per_section=3)

    # Then
    selected = [
        article
        for section_articles in briefing.sections.values()
        for article in section_articles
    ]
    assert len(selected) == 2


def test_build_briefing_collapses_same_corporate_ownership_event() -> None:
    # Given
    published = datetime(2026, 7, 10, 6, 0, tzinfo=UTC)
    articles = [
        _article(
            "한화, KAI 지분 확대…연말 최대 15% 확보 추진",
            "뉴스저널리즘",
            Section.POLICY,
            published,
        ),
        _article(
            "한화, KAI에 2.5조 베팅…육해공 통합 방산 퍼즐 맞춘다",
            "아시아투데이",
            Section.POLICY,
            published,
        ),
        _article(
            "KAI KF-21 시험비행에 한화시스템 레이더 투입",
            "국방일보",
            Section.WEAPON_SYSTEM,
            published,
        ),
    ]

    # When
    briefing = build_briefing(articles, max_per_section=3)

    # Then
    selected = [
        article
        for section_articles in briefing.sections.values()
        for article in section_articles
    ]
    assert len(selected) == 2


def _article(
    title: str,
    source: str,
    section: Section,
    published_at: datetime,
) -> Article:
    return Article(
        title=title,
        url=f"https://example.com/{len(title)}-{source}",
        published_at=published_at,
        source=source,
        section=section,
    )
