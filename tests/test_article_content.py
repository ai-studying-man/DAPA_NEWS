from __future__ import annotations

from unittest.mock import patch

from dapa_morning_brief.article_content import extract_main_text, resolve_article_url


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
