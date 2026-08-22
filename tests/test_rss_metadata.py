from datetime import UTC, datetime

from dapa_morning_brief.rss_parser import parse_rss_items


def test_parse_rss_items_removes_known_domain_suffixes_from_titles() -> None:
    # Given
    xml = (
        "<rss><channel>"
        "<item>"
        "<title>방산 수출 확대 - v.daum.net</title>"
        "<link>https://example.com/daum</link>"
        "<pubDate>Sat, 22 Aug 2026 01:00:00 GMT</pubDate>"
        "<source>Google News</source>"
        "</item>"
        "<item>"
        "<title>방위산업 무인체계 기술 협력 [newfilenews.com]</title>"
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
        "방산 수출 확대",
        "방위산업 무인체계 기술 협력",
    ]
