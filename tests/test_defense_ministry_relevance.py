from datetime import UTC, datetime
from unittest import TestCase

from dapa_morning_brief.models import Section
from dapa_morning_brief.rss_parser import (
    classify_title,
    is_relevant_title,
    parse_rss_items,
)


class DefenseMinistryRelevanceTest(TestCase):
    def test_defense_ministry_news_is_classified_as_government(self) -> None:
        # Given
        titles = (
            "국방부, AI 기반 무인화 전력 운용 확대",
            "국방부, 장병 복무여건 개선대책 발표",
        )

        # When
        results = tuple(
            (is_relevant_title(title), classify_title(title)) for title in titles
        )

        # Then
        assert results == (
            (True, Section.GOVERNMENT),
            (True, Section.GOVERNMENT),
        )

    def test_rss_source_metadata_routes_defense_ministry_to_government(self) -> None:
        # Given
        xml = """
        <rss>
          <channel>
            <item>
              <title>장병 복무여건 개선대책 발표</title>
              <link>https://example.com/ministry-policy</link>
              <source>국방부</source>
              <pubDate>Wed, 05 Aug 2026 22:00:00 GMT</pubDate>
            </item>
          </channel>
        </rss>
        """

        # When
        articles = parse_rss_items(
            xml,
            source_name="Google News",
            default_section=None,
            days=1,
            now=datetime(2026, 8, 6, 0, 0, tzinfo=UTC),
        )

        # Then
        assert [article.section for article in articles] == [Section.GOVERNMENT]
