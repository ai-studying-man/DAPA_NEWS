from __future__ import annotations

from datetime import UTC, datetime

from dapa_morning_brief.briefing import build_briefing
from dapa_morning_brief.models import Article, Section
from dapa_morning_brief.story_deduplication import are_same_story


def test_same_story_when_kai_acquisition_series_header_matches() -> None:
    # Given
    first_title = (
        "[불붙는 KAI 인수전] 알박기 한화 VS 수싸움 현대차...내년이 분수령"
        " - 아주경제"
    )
    second_title = (
        "[불붙는 KAI 인수전] 비싸진 몸값에 독과점 논란까지...분할 매각안 솔솔"
        " - 아주경제"
    )

    # When
    same_story = are_same_story(first_title, second_title)

    # Then
    assert same_story is True


def test_build_briefing_selects_most_viewed_original_from_duplicate_story() -> None:
    # Given
    published = datetime(2026, 7, 15, 5, 30, tzinfo=UTC)
    articles = [
        Article(
            title=(
                "[불붙는 KAI 인수전] 알박기 한화 VS 수싸움 현대차"
                "...내년이 분수령 - 아주경제"
            ),
            url="https://example.com/lower-views",
            published_at=published,
            source="아주경제",
            section=Section.POLICY,
            view_count=1200,
        ),
        Article(
            title=(
                "[불붙는 KAI 인수전] 비싸진 몸값에 독과점 논란까지"
                "...분할 매각안 솔솔 - 아주경제"
            ),
            url="https://example.com/higher-views",
            published_at=published,
            source="아주경제",
            section=Section.POLICY,
            view_count=4500,
        ),
    ]

    # When
    briefing = build_briefing(articles, max_per_section=3)

    # Then
    assert [article.url for article in briefing.sections[Section.POLICY]] == [
        "https://example.com/higher-views",
    ]
    assert [article.title for article in briefing.sections[Section.POLICY]] == [
        articles[1].title,
    ]


def test_build_briefing_uses_rss_description_to_detect_duplicate_story() -> None:
    # Given
    published = datetime(2026, 7, 15, 5, 30, tzinfo=UTC)
    shared_description = (
        "한화가 산업은행 보유 한국항공우주 KAI 지분 인수를 추진하는 내용"
    )
    articles = [
        Article(
            title="한화, 항공산업 재편 본격화",
            url="https://example.com/first",
            published_at=published,
            source="뉴스A",
            section=Section.POLICY,
            description=shared_description,
            view_count=300,
        ),
        Article(
            title="산은 보유지분 향방 주목",
            url="https://example.com/second",
            published_at=published,
            source="뉴스B",
            section=Section.POLICY,
            description=f"{shared_description}을 업계가 주목하고 있다",
            view_count=900,
        ),
    ]

    # When
    briefing = build_briefing(articles, max_per_section=3)

    # Then
    assert [article.url for article in briefing.sections[Section.POLICY]] == [
        "https://example.com/second",
    ]


def test_build_briefing_uses_feed_prominence_when_views_are_unavailable() -> None:
    # Given
    published = datetime(2026, 7, 15, 5, 30, tzinfo=UTC)
    articles = [
        Article(
            title="[KAI 인수전] 지분 매각 쟁점 부상",
            url="https://example.com/lower-feed-position",
            published_at=published,
            source="뉴스A",
            section=Section.POLICY,
            feed_rank=4,
        ),
        Article(
            title="[KAI 인수전] 한화·현대차 경쟁 구도",
            url="https://example.com/higher-feed-position",
            published_at=published,
            source="뉴스B",
            section=Section.POLICY,
            feed_rank=0,
        ),
    ]

    # When
    briefing = build_briefing(articles, max_per_section=3)

    # Then
    assert [article.url for article in briefing.sections[Section.POLICY]] == [
        "https://example.com/higher-feed-position",
    ]


def test_build_briefing_collapses_july_sixteen_cluster_launch_coverage() -> None:
    # Given
    published = datetime(2026, 7, 16, 0, 0, tzinfo=UTC)
    articles = [
        _article(
            "인천 방산혁신클러스터 조성 '탄력'···엣지AI 기반 항공·우주 특화",
            "인천투데이",
            Section.POLICY,
            published,
        ),
        _article(
            "전국 4개 권역 방산혁신클러스터 출범",
            "굿모닝충청",
            Section.EXPORT_BUSINESS,
            published,
        ),
        _article(
            "전북 방산혁신클러스터 구축 본격화…K-방산 소재·부품 거점 조성",
            "천지일보",
            Section.EXPORT_BUSINESS,
            published,
        ),
        _article(
            "방사청, 전북·경남·충남·인천 등과 방산혁신단지 업무협약",
            "SPN 서울평양뉴스",
            Section.EXPORT_BUSINESS,
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
    assert len(selected) == 1


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
