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
    def test_parse_rss_rejects_comment_and_premium_content(self) -> None:
        xml = """
        <rss>
          <channel>
            <item>
              <title>댓글 : 방사청 내부 문서 유출?! TFA-50의 정체는?</title>
              <link>https://example.com/comment</link>
              <source>네이버 프리미엄콘텐츠</source>
              <pubDate>Sat, 18 Jul 2026 22:00:00 GMT</pubDate>
            </item>
            <item>
              <title>방사청 FA-50 수출예비승인 포착</title>
              <link>https://example.com/premium</link>
              <source>네이버 프리미엄콘텐츠</source>
              <pubDate>Sat, 18 Jul 2026 22:10:00 GMT</pubDate>
            </item>
          </channel>
        </rss>
        """

        articles = parse_rss_items(
            xml,
            source_name="Google News",
            default_section=None,
            days=1,
            now=datetime(2026, 7, 19, 0, 0, tzinfo=UTC),
        )

        assert articles == []

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

    def test_parse_rss_classifies_government_actor_in_description(self) -> None:
        xml = """
        <rss>
          <channel>
            <item>
              <title>K-방산 소재·부품 공급망 안정화 대책 발표</title>
              <link>https://example.com/government-policy</link>
              <description>정부가 방산 공급망 지원 정책을 발표했다.</description>
              <source>정책뉴스</source>
              <pubDate>Wed, 15 Jul 2026 22:00:00 GMT</pubDate>
            </item>
          </channel>
        </rss>
        """

        articles = parse_rss_items(
            xml,
            source_name="test",
            default_section=None,
            days=1,
            now=datetime(2026, 7, 16, 0, 0, tzinfo=UTC),
        )

        assert len(articles) == 1
        assert articles[0].section is Section.GOVERNMENT

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

    def test_major_current_government_policy_is_classified_as_government(
        self,
    ) -> None:
        titles = [
            "이 대통령, 업무보고서 개혁·혁신 잘돼야…남은 기간 더 중요",
            "이 대통령 주재 국무회의 AI기본법 시행령 등 21건 의결",
            "대통령, 국무회의서 AI기본법 시행령 의결",
            "대통령실, 국민참여 업무보고 일정 공개",
            "정부, 국정과제 성과 점검 결과 발표",
        ]

        for title in titles:
            with self.subTest(title=title):
                assert is_relevant_title(title) is True
                assert classify_title(title) is Section.GOVERNMENT

    def test_dapa_institutional_policy_topics_are_relevant(self) -> None:
        titles = [
            "국방첨단인증 공청회 개최…AI·우주·드론 기술 국방 활용 확대",
            "방위사업청·국방기술품질원, 2026 국방품질 종합학술대회 개최",
            "충남·논산 방산혁신클러스터 본격화…K-방산 도약 발판",
            "법원, K5방독면 국방규격 속 특허 인정…타 업체 침해 안돼",
        ]

        for title in titles:
            with self.subTest(title=title):
                assert is_relevant_title(title) is True
                assert classify_title(title) is Section.POLICY

    def test_export_event_outweighs_weapon_terms(self) -> None:
        titles = [
            "글로벌 함정 수출 2막 열린다…K조선 특수선 시장 정조준",
            "K-방산 수출 늘수록 무기체계 공급망 안정화 숙제",
        ]

        for title in titles:
            with self.subTest(title=title):
                assert classify_title(title) is Section.EXPORT_BUSINESS

    def test_named_domestic_weapon_program_needs_no_extra_anchor(self) -> None:
        title = "238억 잠수함 링크-22 사업 추진"

        assert is_relevant_title(title) is True
        assert classify_title(title) is Section.WEAPON_SYSTEM

    def test_configured_defense_queries_survive_relevance_filter(self) -> None:
        expectations = {
            "한국 해군 차세대 호위함 건조 본격화": Section.WEAPON_SYSTEM,
            "NATO 품질인증 획득…글로벌 공략 속도": Section.EXPORT_BUSINESS,
        }

        for title, expected in expectations.items():
            with self.subTest(title=title):
                assert is_relevant_title(title) is True
                assert classify_title(title) is expected

    def test_generic_government_decree_without_defense_context_is_rejected(
        self,
    ) -> None:
        title = "정부, 민법 시행령 개정안 국무회의 의결"

        assert is_relevant_title(title) is False
        assert classify_title(title) is not Section.GOVERNMENT

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
