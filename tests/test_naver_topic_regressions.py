from dataclasses import replace
from datetime import UTC, datetime, timedelta
from xml.sax.saxutils import escape

import pytest

from dapa_morning_brief.briefing import build_briefing
from dapa_morning_brief.models import Article, Section
from dapa_morning_brief.naver_news import parse_naver_items
from dapa_morning_brief.rss_parser import classify_title, is_relevant_article
from dapa_morning_brief.story_deduplication import are_same_articles


@pytest.mark.parametrize(
    ("title", "description", "expected"),
    [
        (
            "KF-21 '보라매' 적용한 국제표준 기술교범, K2 '흑표' 등 확대",
            "방사청은 해외 수출품들에 S1000D 적용을 확대해 수출 경쟁력을 높인다.",
            Section.POLICY,
        ),
        (
            "방사청, KF-21 기술교범 개발 경험 국제 공유…K-방산 표준화 확대",
            "국제표준 S1000D와 후속군수지원 방안을 소개했다.",
            Section.POLICY,
        ),
        (
            "나우로보틱스가 방산에 뛰어든다…국방 로봇·군수 MRO까지 확대",
            "방위사업청은 로봇·AI·우주·드론을 국방 첨단전략산업으로 지정했다.",
            Section.EXPORT_BUSINESS,
        ),
        (
            "KAI, 멕시코 항공우주산업협회와 MOU…중남미 사업 확대 모색",
            "방사청은 KF-21 개발과 방산 지원 정책을 추진하고 있다.",
            Section.EXPORT_BUSINESS,
        ),
        (
            "K2 전차 국내 양산 계약 체결",
            "폴란드 수출 성과에 이어 방사청의 국방 AI 정책이 주목된다.",
            Section.WEAPON_SYSTEM,
        ),
    ],
)
def test_headline_topic_survives_naver_background(
    title: str,
    description: str,
    expected: Section,
) -> None:
    # Given / When
    result = classify_title(title, description=description, source="연합뉴스")
    # Then
    assert result is expected


@pytest.mark.parametrize(
    "title",
    [
        "[포토타임] 78년 검찰청 간판 내렸다…수사·기소 분리 D-4",
        "[사설] 학벌과 나이에 갇힌 기업의 미래는 없다",
        "재벌총수 망신주기 국감 단골소재?",
        "화장품 기업, 해외 진출 확대…관세 대응책 논의",
    ],
)
def test_incidental_defense_snippet_cannot_establish_relevance(title: str) -> None:
    # Given
    description = "한화의 방산 수출과 국방 AI 사업도 함께 언급됐다."
    # When
    relevant = is_relevant_article(title, description, "연합뉴스")
    # Then
    assert not relevant


def test_unknown_topic_is_not_assigned_to_policy() -> None:
    # Given / When
    section = classify_title("업계 관계자들의 다양한 의견 소개")
    # Then
    assert section is None


def test_country_name_is_not_a_delivery_action() -> None:
    # Given / When
    section = classify_title("KAI, 인도네시아와 KF-21 국내개발 시험평가 완료")
    # Then
    assert section is Section.WEAPON_SYSTEM


def test_latest_duplicate_is_selected_before_category_quota() -> None:
    # Given
    older = Article(
        title="한화 방산 3사, 군인 가족 초청 힐링데이",
        url="https://example.com/older",
        published_at=datetime(2026, 9, 28, tzinfo=UTC),
        source="연합뉴스",
        section=Section.POLICY,
    )
    newer = replace(
        older,
        url="https://example.com/newer",
        published_at=older.published_at + timedelta(hours=1),
        section=Section.EXPORT_BUSINESS,
    )
    # When
    briefing = build_briefing([older, newer], max_per_section=5)
    # Then
    assert [a.url for bucket in briefing.sections.values() for a in bucket] == [
        newer.url
    ]


@pytest.mark.parametrize(
    ("left_title", "right_title"),
    [
        ("K2 전차 폴란드 수출 계약 체결", "K2 전차 루마니아 수출 계약 체결"),
        ("K2 전차 폴란드 수출 계약 체결", "K2 전차 폴란드 인도 완료"),
        ("K2 전차 폴란드 수출 계약 체결", "K2 전차 폴란드 수출 계약 취소"),
    ],
)
def test_shared_background_cannot_merge_distinct_events(
    left_title: str,
    right_title: str,
) -> None:
    # Given
    left = Article(
        title=left_title,
        url="https://example.com/left",
        published_at=datetime(2026, 9, 28, tzinfo=UTC),
        source="연합뉴스",
        section=Section.EXPORT_BUSINESS,
        description="K2 전차는 한국 방산 수출의 대표적인 무기체계로 주목받는다.",
    )
    right = replace(left, title=right_title, url="https://example.com/right")
    # When
    same = are_same_articles(
        left, right, left_body=left.description * 8, right_body=right.description * 8
    )
    # Then
    assert not same


def test_naver_feed_keeps_one_manual_standardization_event() -> None:
    # Given: differently worded reports of the September 28 announcement.
    titles = (
        "KF-21 '보라매' 적용한 국제표준 기술교범, K2 '흑표' 등 확대",
        "방사청, 무기체계 기술교범 국제표준화 확대…K-방산 수출 경쟁력 강화",
        "방사청, KF-21 기술교범 개발 경험 국제 공유…K-방산 표준화 확대",
    )
    items = "".join(
        "".join(
            (
                f"<item><title>{escape(title)}</title>",
                f"<originallink>https://example.com/{index}</originallink>",
                f"<link>https://news.naver.com/{index}</link>",
                "<description>",
                "방사청은 S1000D 국제표준 기술교범 적용을 확대했다.",
                "</description>",
                "<pubDate>Mon, 28 Sep 2026 01:00:00 GMT</pubDate></item>",
            )
        )
        for index, title in enumerate(titles)
    )
    # When
    articles = parse_naver_items(
        f"<rss><channel>{items}</channel></rss>",
        days=1,
        now=datetime(2026, 9, 28, 6, tzinfo=UTC),
    )
    briefing = build_briefing(articles, max_per_section=5)
    # Then
    assert len(articles) == 3
    assert [len(briefing.sections[section]) for section in Section] == [0, 1, 0, 0]
