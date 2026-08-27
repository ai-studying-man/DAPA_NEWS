from datetime import UTC, datetime

from dapa_morning_brief.rss_parser import parse_rss_items


def test_parse_rss_items_uses_upcoming_send_window_during_0545_collection() -> None:
    # Given
    xml = """
    <rss>
      <channel>
        <item>
          <title>방위사업청, 국방획득 제도 개선</title>
          <link>https://example.com/stale-before-collection</link>
          <pubDate>Tue, 07 Jul 2026 21:29:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """

    # When
    articles = parse_rss_items(
        xml,
        source_name="test",
        default_section=None,
        days=1,
        now=datetime(2026, 7, 8, 20, 45, tzinfo=UTC),
    )

    # Then
    assert articles == []
