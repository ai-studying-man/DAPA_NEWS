from dataclasses import replace
from datetime import UTC, datetime, timedelta

from dapa_morning_brief.briefing import build_briefing
from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.models import Article, Section
from dapa_morning_brief.story_deduplication import are_same_articles

TITLES = (
    "김병주 의원 대통령 국방정책특별보좌관 위촉",
    "평화외교특보 6선 송영길…국방정책특보 4성 장군 출신 김병주",
    "지방시대위원장 박정현…평화외교특보 송영길, 국방정책특보 김병주",
)


def article(title: str, index: int = 0) -> Article:
    return Article(
        title=title,
        url=f"https://example.com/{index}",
        published_at=datetime(2026, 10, 1, tzinfo=UTC),
        source="뉴스",
        section=Section.GOVERNMENT,
    )


def test_one_selection_when_appointment_reports_have_different_leads() -> None:
    # Given
    articles = [article(title, index) for index, title in enumerate(TITLES)]
    leads = (
        "대통령은 김병주 의원을 국방정책특별보좌관으로 위촉했다.",
        "청와대는 국방정책특보에 김병주 의원을 임명했다고 발표했다.",
        "대통령이 국방정책특보 김병주 의원을 위촉하며 인선을 발표했다.",
    )
    bodies = [
        ArticleBody(
            article_url=item.url,
            title=item.title,
            source=item.source,
            body=lead + " " + " ".join(f"보도{index}사항{word}" for word in range(100)),
        )
        for index, (item, lead) in enumerate(zip(articles, leads, strict=True))
    ]
    # When
    briefing = build_briefing(articles, max_per_section=5, article_bodies=bodies)
    # Then
    assert len(briefing.sections[Section.GOVERNMENT]) == 1


def test_preserve_distinct_events_when_roles_people_or_actions_differ() -> None:
    # Given
    first = article(TITLES[0])
    controls = (
        "홍길동 의원 대통령 국방정책특별보좌관 위촉",
        "김병주 의원 대통령 평화외교특별보좌관 위촉",
        "국방정책특보 김병주 부대 방문",
        "국방정책특보 김병주 정책 연설",
        "김병주 대통령 국방정책특별보좌관 위촉 철회",
        "김병주 대통령 국방정책특별보좌관 해임",
        "김병주 국방정책특보 관련 정책 논쟁",
    )
    # When / Then
    for title in controls:
        assert not are_same_articles(first, article(title, 1)), title


def test_preserve_later_appointment_when_dates_exceed_two_days() -> None:
    # Given
    first = article(TITLES[0])
    second = Article(
        title=TITLES[1],
        url="https://example.com/later",
        published_at=first.published_at + timedelta(days=3),
        source="뉴스",
        section=Section.GOVERNMENT,
    )
    # When / Then
    assert not are_same_articles(first, second)


def test_preserve_topic_when_appointment_is_only_background() -> None:
    # Given
    first = article(TITLES[0])
    second = article("국방정책특보 김병주 정책 논쟁", 1)
    # When / Then
    assert not are_same_articles(
        first,
        second,
        right_body=(
            "군 예산안 심의가 국회에서 열렸다. 과거 대통령은 김병주 의원을 "
            "국방정책특보로 위촉했다."
        ),
    )


def test_same_appointment_when_substantial_bodies_have_distinct_wording() -> None:
    # Given
    first, second = article(TITLES[0]), article(TITLES[1], 1)
    left = "대통령은 김병주 의원을 국방정책특별보좌관으로 위촉했다. " + " ".join(
        f"가나다{i}" for i in range(100)
    )
    right = "청와대는 국방정책특보에 김병주 의원을 임명했다고 발표했다. " + " ".join(
        f"라마바{i}" for i in range(100)
    )
    # When
    same = are_same_articles(first, second, left_body=left, right_body=right)
    # Then
    assert same


def test_same_appointment_when_office_words_are_spaced() -> None:
    # Given
    first = article(TITLES[0])
    second = article("대통령 국방정책 특보 김병주 임명", 1)
    # When
    same = are_same_articles(first, second)
    # Then
    assert same


def test_one_global_story_when_appointment_listing_bodies_are_unavailable() -> None:
    # Given
    titles = (
        *TITLES,
        "대통령 국방정책 특보된 김병주 의원",
        "[속보] 대통령 평화외교 특보 송영길·국방정책 특보 김병주",
    )
    articles = [
        replace(
            article(title, index),
            section=Section.POLICY if index < 3 else Section.GOVERNMENT,
        )
        for index, title in enumerate(titles)
    ]
    # When
    briefing = build_briefing(articles, max_per_section=5)
    # Then
    assert sum(len(items) for items in briefing.sections.values()) == 1


def test_preserve_distinct_list_when_one_appointee_changes() -> None:
    # Given
    first = article(TITLES[1])
    second = article("평화외교특보 송영길·국방정책특보 홍길동 위촉", 1)
    # When
    same = are_same_articles(first, second)
    # Then
    assert not same


def test_preserve_topic_list_when_headline_compares_existing_officials() -> None:
    # Given
    first = article(TITLES[1])
    second = article("평화외교특보 송영길·국방정책특보 김병주 정책 비교", 1)
    # When
    same = are_same_articles(first, second)
    # Then
    assert not same
