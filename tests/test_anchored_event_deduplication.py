from datetime import UTC, datetime

from dapa_morning_brief.models import Article, Section
from dapa_morning_brief.story_deduplication import are_same_articles


def article(title: str, url: str) -> Article:
    return Article(
        title=title,
        url=url,
        published_at=datetime(2026, 10, 12, tzinfo=UTC),
        source="뉴스",
        section=Section.POLICY,
    )


def test_same_flight_when_languages_differ() -> None:
    # Given
    left = article(
        "FA-50 전투기와 무인기, 고흥 앞바다서 국내 첫 편대비행", "https://a.test/1"
    )
    right = article(
        "KAI Flies FA-50 and AAP Drone Just 9 Meters Apart", "https://b.test/1"
    )
    korean = (
        "KAI는 지난 8일 고흥에서 FA-50과 AAP의 편대비행을 실시했다. 20분 동안 비행했다."
    )
    english = (
        "KAI conducted a formation flight of FA-50 and AAP drone on October 8 "
        "over Goheung. The aircraft flew for 20 minutes."
    )
    # When
    same = are_same_articles(left, right, left_body=korean, right_body=english)
    # Then
    assert same


def test_different_flights_when_event_dates_differ() -> None:
    # Given
    left = article("FA-50과 AAP 편대비행", "https://a.test/1")
    right = article("FA-50 and AAP formation flight", "https://b.test/1")
    # When
    same = are_same_articles(
        left,
        right,
        left_body="10월 8일 FA-50과 AAP 편대비행은 20분간 진행됐다.",
        right_body="October 9 FA-50 and AAP formation flight lasted 20 minutes.",
    )
    # Then
    assert not same


def test_same_opening_when_headlines_and_substantial_bodies_differ() -> None:
    # Given
    left = article("국방부, 첫 번째 '국방 AX 거점' 개소식 개최", "https://a.test/1")
    right = article("국방부, 판교에 첫 'AX 거점' 개소", "https://b.test/1")
    korean = (
        "국방부가 12일 판교에서 국방 AX 거점 개소식을 개최했다. "
        + "민군 협력 연구 기술 참여 기반 마련을 추진한다. " * 8
    )
    other = (
        "12일 판교 국방 AX 거점이 개소했다. "
        + "기업의 인공지능 전환 지원과 실증 환경 제공으로 발전을 도모한다. " * 8
    )
    # When
    same = are_same_articles(left, right, left_body=korean, right_body=other)
    # Then
    assert same


def test_different_flights_when_location_is_only_changed_fact() -> None:
    # Given
    left = article("FA-50과 AAP 편대비행", "https://a.test/1")
    right = article("FA-50 and AAP formation flight", "https://b.test/1")
    # When
    same = are_same_articles(
        left,
        right,
        left_body="10월 8일 고흥에서 FA-50과 AAP 편대비행은 20분간 진행됐다.",
        right_body=(
            "October 8 at Sacheon FA-50 and AAP formation flight lasted 20 minutes."
        ),
    )
    # Then
    assert not same


def test_different_openings_when_same_day_events_have_distinct_sites() -> None:
    # Given
    left = article("국방부 판교 AX 거점 개소", "https://a.test/1")
    right = article("국방부 대전 AX 거점 개소", "https://b.test/1")
    first = (
        "국방부는 12일 판교에서 강신철 장관 주관으로 국방 AX 거점 개소식을 개최했다."
    )
    second = (
        "국방부는 12일 대전에서 강신철 장관 주관으로 국방 AX 거점 개소식을 개최했다."
    )
    # When
    same = are_same_articles(left, right, left_body=first, right_body=second)
    # Then
    assert not same


def test_distinct_opening_sites_when_both_reports_list_future_centers() -> None:
    # Given
    left = article("국방부 판교 AX 거점 개소", "https://a.test/1")
    right = article("국방부 대전 AX 거점 개소", "https://b.test/1")
    background = " 앞으로 판교 대전 부산 양재 용산 거점을 운영한다."
    first = "국방부는 12일 판교에서 강신철 장관 주관으로 AX 거점을 개소했다."
    second = "국방부는 12일 대전에서 강신철 장관 주관으로 AX 거점을 개소했다."
    # When
    same = are_same_articles(
        left, right, left_body=first + background, right_body=second + background
    )
    # Then
    assert not same
