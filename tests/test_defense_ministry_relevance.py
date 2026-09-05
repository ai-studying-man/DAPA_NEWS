from datetime import UTC, datetime
from unittest import TestCase

from dapa_morning_brief.models import Section
from dapa_morning_brief.rss_parser import (
    classify_title,
    is_relevant_article,
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

    def test_unrelated_foreign_defense_ministry_news_is_rejected(self) -> None:
        # Given
        titles = (
            '국방부 "무력으로 타이완 독립 꾀하는 어떤 시도든 반드시 실패" - 国际在线',
            "타이완 국방부, 미사일 시험 실시",
            "중국 국방부, 신형 미사일 시험",
            "일본 방위성, 방위정책 발표",
        )

        # When
        results = tuple(is_relevant_title(title) for title in titles)

        # Then
        assert results == (False, False, False, False)

    def test_united_states_defense_ministry_news_remains_government(self) -> None:
        # Given
        titles = (
            "미 국방부, 인도태평양 방위정책 발표",
            "美 국방부, 한미동맹 강화 방안 발표",
            "미국 국방부, 새로운 국방정책 발표",
        )

        # When
        results = tuple(
            (is_relevant_title(title), classify_title(title)) for title in titles
        )

        # Then
        assert results == (
            (True, Section.GOVERNMENT),
            (True, Section.GOVERNMENT),
            (True, Section.GOVERNMENT),
        )

    def test_foreign_country_source_does_not_make_bare_ministry_domestic(
        self,
    ) -> None:
        # Given
        articles = (
            (
                "국방부 불법·비보고·비규제(IUU) 어업 퇴치 운영위원회가 람동 시찰",
                "Vietnam.vn",
            ),
            (
                "국방부, 럼동성서 IUU 어업 근절 실태 점검",
                "Thông tấn xã Việt Nam",
            ),
        )

        # When
        results = tuple(
            is_relevant_article(title, "", source) for title, source in articles
        )

        # Then
        assert results == (False, False)

    def test_foreign_ministry_news_keeps_korean_weapon_programs(self) -> None:
        # Given
        title = "폴란드 국방부, K9 자주포 추가 도입 결정"

        # When
        result = is_relevant_title(title), classify_title(title)

        # Then
        assert result == (True, Section.WEAPON_SYSTEM)

    def test_foreign_only_news_is_rejected_across_all_sections(self) -> None:
        # Given
        articles = (
            ("브라질 국방부, 신형 미사일 시험", ""),
            ("대만의 국방부, 신형 미사일 시험", ""),
            ("중국 국방부, 미 국방부 정책 비판", ""),
            ("이스라엘 방산기업, 신형 드론 공개", ""),
            ("폴란드, 국방비 확대…유럽 방산 공급망 재편", ""),
            ("CIA 벤처 자본이 유럽 신흥 방산 스타트업 키운 속사정", ""),
            ("유럽 방산기업, 대드론 모듈 공개", "데일리방산"),
            ("국내 방산기업, 신형 드론 공개", "Reuters"),
        )

        # When
        results = tuple(
            is_relevant_article(title, "", source) for title, source in articles
        )

        # Then
        assert results == (False, False, False, False, False, False, False, False)

    def test_confirmed_korean_or_us_defense_news_is_allowed(self) -> None:
        # Given
        titles = (
            "국방부, 서울안보대화 개최",
            "방위사업청, 국방획득 제도 개선",
            "현대로템, 폴란드 K2 전차 추가 수출",
            "미 국방부, 인도태평양 방위정책 발표",
            "美 육군, 차세대 무인체계 도입",
        )

        # When
        results = tuple(is_relevant_title(title) for title in titles)

        # Then
        assert results == (True, True, True, True, True)

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
