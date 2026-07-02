from __future__ import annotations

from datetime import UTC, datetime
from unittest import TestCase

from dapa_morning_brief.models import Section
from dapa_morning_brief.rss_parser import (
    classify_title,
    is_relevant_title,
    parse_rss_items,
)


class RelevanceFilterTest(TestCase):
    def test_government_news_requires_defense_context(self) -> None:
        # Given
        title = "이재명 대통령, 민생경제 회복 대책 회의 주재"

        # When
        is_relevant = is_relevant_title(title)

        # Then
        assert is_relevant is False

    def test_government_defense_news_is_classified_as_government(self) -> None:
        # Given
        title = "국방부 장관, 방산수출 확대와 무기체계 전력화 점검"

        # When
        section = classify_title(title)

        # Then
        assert section == Section.GOVERNMENT

    def test_parse_rss_items_rejects_missing_pub_date(self) -> None:
        # Given
        xml = """
        <rss>
          <channel>
            <item>
              <title>방위사업청, 무기체계 시험평가 제도 개선</title>
              <link>https://example.com/no-date</link>
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
            now=datetime(2026, 7, 2, 6, 30, tzinfo=UTC),
        )

        # Then
        assert articles == []

    def test_parse_rss_items_rejects_old_article(self) -> None:
        # Given
        xml = """
        <rss>
          <channel>
            <item>
              <title>방위사업청, 무기체계 시험평가 제도 개선</title>
              <link>https://example.com/old</link>
              <pubDate>Mon, 29 Jun 2026 00:00:00 GMT</pubDate>
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
            now=datetime(2026, 7, 2, 6, 30, tzinfo=UTC),
        )

        # Then
        assert articles == []
