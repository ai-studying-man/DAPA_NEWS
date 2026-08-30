from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import patch

import httpx

from dapa_morning_brief.article_content import (
    _filter_articles_by_publisher_date,
    extract_main_text,
    fetch_article_bodies,
    resolve_article_url,
)
from dapa_morning_brief.models import Article, Briefing, Section


def test_extract_main_text_removes_navigation_and_keeps_article() -> None:
    # Given
    html = """
    <html><body>
      <nav>홈 정치 경제 사회 로그인</nav>
      <article>
        <h1>방산 수출 계약 체결</h1>
        <p>정부와 기업은 수출 계약의 후속 이행 일정을 확정했다.</p>
        <p>초도 물량의 납품은 내년부터 단계적으로 진행될 예정이다.</p>
      </article>
      <footer>회사 소개 개인정보 처리방침</footer>
    </body></html>
    """

    # When
    body = extract_main_text(html)

    # Then
    assert body is not None
    assert "후속 이행 일정" in body
    assert "개인정보 처리방침" not in body


def test_resolve_article_url_decodes_google_news_link() -> None:
    # Given
    google_url = "https://news.google.com/rss/articles/encoded"
    publisher_url = "https://publisher.example.com/news/1"
    decoder_result = {"status": True, "decoded_url": publisher_url}

    # When
    with patch(
        "dapa_morning_brief.article_content.gnewsdecoder",
        return_value=decoder_result,
    ):
        resolved = resolve_article_url(google_url)

    # Then
    assert resolved == publisher_url


def test_fetch_article_bodies_skips_sections_without_practice_points() -> None:
    # Given
    published = datetime(2026, 8, 6, tzinfo=UTC)
    government = Article(
        title="국방부 정책 발표",
        url="https://example.com/government",
        published_at=published,
        source="정부뉴스",
        section=Section.GOVERNMENT,
    )
    policy = Article(
        title="방위사업 조달 정책 발표",
        url="https://example.com/policy",
        published_at=published,
        source="정책뉴스",
        section=Section.POLICY,
    )
    briefing = Briefing(
        sections={
            Section.GOVERNMENT: (government,),
            Section.POLICY: (policy,),
            Section.WEAPON_SYSTEM: (),
            Section.EXPORT_BUSINESS: (),
        },
    )
    response = httpx.Response(
        200,
        text="<article><p>방위사업 조달 정책의 적용 일정을 확정했다.</p></article>",
        request=httpx.Request("GET", policy.url),
    )

    # When
    with (
        patch.object(httpx.Client, "get", return_value=response) as get,
        patch(
            "dapa_morning_brief.article_content.extract_main_text",
            return_value="방위사업 조달 정책의 적용 일정을 확정했다.",
        ),
    ):
        bodies = fetch_article_bodies(briefing)

    # Then
    assert [body.article_url for body in bodies] == [policy.url]
    assert get.call_count == 1


def test_publisher_date_filter_rejects_resurfaced_old_google_article() -> None:
    # Given
    article = Article(
        title="미래를 위한 새로운 시작, 2021 방위사업청",
        url="https://news.google.com/rss/articles/old",
        published_at=datetime(2026, 8, 29, 6, 10, tzinfo=UTC),
        source="대한민국 정책브리핑",
        section=Section.POLICY,
    )
    response = httpx.Response(
        200,
        text=(
            '<html><head><meta property="article:published_time" '
            'content="2021-10-22T09:00:00+09:00"></head></html>'
        ),
        request=httpx.Request("GET", "https://www.korea.kr/old"),
    )

    # When
    with (
        patch(
            "dapa_morning_brief.article_content.resolve_article_url",
            return_value="https://www.korea.kr/old",
        ),
        patch.object(httpx.Client, "get", return_value=response),
    ):
        result = _filter_articles_by_publisher_date(
            [article],
            as_of=date(2026, 8, 30),
            max_age_days=2,
        )

    # Then
    assert result.articles == ()
    assert result.checked_google == 1
    assert result.unverifiable == 0
    assert [(item.title, item.publisher_date) for item in result.rejected] == [
        (article.title, date(2021, 10, 22)),
    ]


def test_publisher_date_filter_keeps_current_and_excludes_unverifiable(
) -> None:
    # Given
    current = Article(
        title="방위사업청, 최신 조달지침 발표",
        url="https://news.google.com/rss/articles/current",
        published_at=datetime(2026, 8, 29, 7, tzinfo=UTC),
        source="테스트뉴스",
        section=Section.POLICY,
    )
    unavailable = Article(
        title="방위사업청, 시험평가 일정 점검",
        url="https://news.google.com/rss/articles/unavailable",
        published_at=datetime(2026, 8, 29, 8, tzinfo=UTC),
        source="테스트뉴스",
        section=Section.POLICY,
    )
    current_response = httpx.Response(
        200,
        text=(
            '<html><head><meta property="article:published_time" '
            'content="2026-08-29T16:00:00+09:00"></head></html>'
        ),
        request=httpx.Request("GET", "https://publisher.example/current"),
    )

    def resolve(url: str) -> str:
        return url.replace("https://news.google.com/rss/articles/", "https://publisher.example/")

    def get(url: str) -> httpx.Response:
        if url.endswith("current"):
            return current_response
        message = "publisher unavailable"
        raise httpx.ConnectError(message)

    # When
    with (
        patch(
            "dapa_morning_brief.article_content.resolve_article_url",
            side_effect=resolve,
        ),
        patch.object(httpx.Client, "get", side_effect=get),
    ):
        result = _filter_articles_by_publisher_date(
            [current, unavailable],
            as_of=date(2026, 8, 30),
            max_age_days=2,
        )

    # Then
    assert result.articles == (current,)
    assert result.checked_google == 2
    assert result.rejected == ()
    assert result.unverifiable == 1
