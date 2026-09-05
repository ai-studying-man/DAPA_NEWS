from datetime import UTC, datetime

from dapa_morning_brief.briefing import build_briefing, format_telegram_message
from dapa_morning_brief.rss_parser import parse_rss_items


def test_parse_rss_items_removes_known_domain_suffixes_from_titles() -> None:
    # Given
    xml = (
        "<rss><channel>"
        "<item>"
        "<title>K-방산 수출 확대 - v.daum.net</title>"
        "<link>https://example.com/daum</link>"
        "<pubDate>Sat, 22 Aug 2026 01:00:00 GMT</pubDate>"
        "<source>Google News</source>"
        "</item>"
        "<item>"
        "<title>한국 방위산업 무인체계 기술 협력 [newfilenews.com]</title>"
        "<link>https://example.com/newfile</link>"
        "<pubDate>Sat, 22 Aug 2026 02:00:00 GMT</pubDate>"
        "<source>Google News</source>"
        "</item>"
        "</channel></rss>"
    )

    # When
    articles = parse_rss_items(
        xml,
        source_name="Google News",
        default_section=None,
        days=1,
        now=datetime(2026, 8, 22, 3, tzinfo=UTC),
    )

    # Then
    assert [article.title for article in articles] == [
        "K-방산 수출 확대",
        "한국 방위산업 무인체계 기술 협력",
    ]


def test_parse_rss_items_removes_publisher_suffixes_from_titles() -> None:
    # Given
    items = (
        (
            "K9 자주포 미국 첫 수출…K방산 새 역사 - yonhapmidas.com",
            "yonhapmidas.com",
        ),
        ("국방부, 장병 복무여건 개선 - 한겨레", "한겨레"),
        (
            "K-방산 경쟁력 강화 - 머니투데이 - 머니투데이",
            "머니투데이",
        ),
        ("방사청, F-15K 성능개량 추진 - 뉴스1", "뉴스1"),
        ("국방부, 2026 서울안보대화 개최:경찰연합신문", "경찰연합신문"),
    )
    xml_items = "".join(
        (
            "<item>"
            f"<title>{title}</title>"
            f"<link>https://example.com/{index}</link>"
            "<pubDate>Sat, 22 Aug 2026 02:00:00 GMT</pubDate>"
            f"<source>{source}</source>"
            "</item>"
        )
        for index, (title, source) in enumerate(items)
    )
    xml = f"<rss><channel>{xml_items}</channel></rss>"

    # When
    articles = parse_rss_items(
        xml,
        source_name="Google News",
        default_section=None,
        days=1,
        now=datetime(2026, 8, 22, 3, tzinfo=UTC),
    )

    # Then
    assert [article.title for article in articles] == [
        "K9 자주포 미국 첫 수출…K방산 새 역사",
        "국방부, 장병 복무여건 개선",
        "K-방산 경쟁력 강화",
        "방사청, F-15K 성능개량 추진",
        "국방부, 2026 서울안보대화 개최",
    ]


def test_title_url_suffix_is_removed_while_article_link_is_preserved() -> None:
    # Given
    article_url = "https://news.example.com/articles/123?src=rss&lang=ko"
    xml = (
        "<rss><channel><item>"
        "<title>K9 자주포 수출 확대 - https://link.com/news/123?src=rss</title>"
        f"<link>{article_url.replace('&', '&amp;')}</link>"
        "<pubDate>Sat, 22 Aug 2026 02:00:00 GMT</pubDate>"
        "<source>Google News</source>"
        "</item></channel></rss>"
    )

    # When
    articles = parse_rss_items(
        xml,
        source_name="Google News",
        default_section=None,
        days=1,
        now=datetime(2026, 8, 22, 3, tzinfo=UTC),
    )
    message = format_telegram_message(
        build_briefing(articles, max_per_section=3),
        today=datetime(2026, 8, 22, tzinfo=UTC).date(),
    )

    # Then
    assert [article.title for article in articles] == ["K9 자주포 수출 확대"]
    assert [article.url for article in articles] == [article_url]
    assert "https://link.com/news/123?src=rss" not in message
    assert 'href="https://news.example.com/articles/123?src=rss&amp;lang=ko"' in message
