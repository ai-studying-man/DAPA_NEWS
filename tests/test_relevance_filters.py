from __future__ import annotations

from datetime import UTC, datetime
from unittest import TestCase

import pytest

from dapa_morning_brief.models import Section
from dapa_morning_brief.rss_parser import (
    MAX_RSS_CHARACTERS,
    classify_title,
    is_relevant_title,
    parse_rss_items,
)


class RelevanceFilterTest(TestCase):
    def test_parse_rss_rejects_oversized_response(self) -> None:
        with pytest.raises(ValueError, match="size limit"):
            _ = parse_rss_items(
                "x" * (MAX_RSS_CHARACTERS + 1),
                source_name="test",
                default_section=None,
                days=1,
                now=datetime(2026, 7, 15, tzinfo=UTC),
            )

    def test_parse_rss_preserves_popularity_and_agency_description(self) -> None:
        # Given
        xml = """
        <rss>
          <channel>
            <item>
              <title>획득제도 개선 설명회 개최</title>
              <link>https://example.com/agency</link>
              <description>방위사업청이 제도 개선 내용을 발표했다.</description>
              <source>일반 언론</source>
              <views>4,500</views>
              <pubDate>Tue, 14 Jul 2026 22:00:00 GMT</pubDate>
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
            now=datetime(2026, 7, 15, 0, 0, tzinfo=UTC),
        )

        # Then
        assert len(articles) == 1
        assert articles[0].description == "방위사업청이 제도 개선 내용을 발표했다."
        assert articles[0].view_count == 4500
        assert articles[0].feed_rank == 0

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

    def test_defense_ai_news_is_classified_as_policy(self) -> None:
        # Given
        title = "국방부, AI 기반 무인화 전력 운용 확대"

        # When
        is_relevant = is_relevant_title(title)
        section = classify_title(title)

        # Then
        assert is_relevant is True
        assert section == Section.POLICY

    def test_ai_news_without_defense_context_is_rejected(self) -> None:
        # Given
        title = "AI 산업 투자 확대에 국내 기업 관심 집중"

        # When
        is_relevant = is_relevant_title(title)

        # Then
        assert is_relevant is False

    def test_ai_drone_news_without_defense_anchor_is_rejected(self) -> None:
        # Given
        title = "영진전문대, AI항공드론과 신설"

        # When
        is_relevant = is_relevant_title(title)

        # Then
        assert is_relevant is False

    def test_parse_rss_items_rejects_article_before_kst_send_window(self) -> None:
        # Given
        xml = """
        <rss>
          <channel>
            <item>
              <title>방위사업청, 국방획득 제도 개선</title>
              <link>https://example.com/before-window</link>
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
            now=datetime(2026, 7, 8, 22, 30, tzinfo=UTC),
        )

        # Then
        assert articles == []

    def test_parse_rss_items_accepts_article_after_kst_send_window(self) -> None:
        # Given
        xml = """
        <rss>
          <channel>
            <item>
              <title>방위사업청, 국방획득 제도 개선</title>
              <link>https://example.com/after-window</link>
              <pubDate>Tue, 07 Jul 2026 21:31:00 GMT</pubDate>
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
            now=datetime(2026, 7, 8, 22, 30, tzinfo=UTC),
        )

        # Then
        assert [article.url for article in articles] == [
            "https://example.com/after-window",
        ]

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
