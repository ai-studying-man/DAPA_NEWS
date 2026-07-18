from datetime import UTC, datetime
from unittest import TestCase

from dapa_morning_brief.models import Section
from dapa_morning_brief.rss_parser import (
    classify_title,
    is_relevant_title,
    parse_rss_items,
)


class CoverageBoundaryTest(TestCase):
    def test_foreign_frigates_without_korean_anchor_are_rejected(self) -> None:
        titles = [
            "영국 해군 호위함, 홍해에 추가 배치",
            "캐나다 해군 호위함, 북대서양 훈련 참가",
            "호주 해군 호위함, 태평양 순찰 시작",
        ]

        for title in titles:
            with self.subTest(title=title):
                assert is_relevant_title(title) is False

    def test_foreign_presidents_do_not_enter_current_government_section(self) -> None:
        titles = [
            "트럼프 대통령, 국무회의서 새 시행령 논의",
            "마크롱 대통령, 경제혁신 업무보고 청취",
            "룰라 대통령, 국정과제 국민참여 확대 발표",
        ]

        for title in titles:
            with self.subTest(title=title):
                assert is_relevant_title(title) is False
                assert classify_title(title) is not Section.GOVERNMENT

    def test_k2_export_contract_survives_rss_boundary(self) -> None:
        xml = """
        <rss>
          <channel>
            <item>
              <title>K2 전차 폴란드 2차 수출 계약 체결</title>
              <link>https://example.com/k2-export</link>
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
        assert articles[0].section is Section.EXPORT_BUSINESS

    def test_k2_domestic_production_contract_stays_weapon_system(self) -> None:
        title = "K2 전차 4차 양산 계약 체결"

        assert is_relevant_title(title) is True
        assert classify_title(title) is Section.WEAPON_SYSTEM

    def test_k9_automotive_news_is_rejected(self) -> None:
        titles = [
            "기아 K9, 2027년형 신차 출시",
            "K9 중고차 시장 가격 상승",
            "기아 K9 글로벌 디자인 공개",
        ]

        for title in titles:
            with self.subTest(title=title):
                assert is_relevant_title(title) is False

    def test_k9_self_propelled_howitzer_news_is_retained(self) -> None:
        expectations = {
            "K9 자주포 3차 양산 착수": Section.WEAPON_SYSTEM,
            "K9 자주포 폴란드 수출 계약": Section.EXPORT_BUSINESS,
        }

        for title, section in expectations.items():
            with self.subTest(title=title):
                assert is_relevant_title(title) is True
                assert classify_title(title) is section

    def test_military_leader_weapon_news_enters_government_section(self) -> None:
        titles = [
            "해군참모총장, 차세대 호위함 전력화 점검",
            "합참의장, 무기체계 전력화 점검",
        ]

        for title in titles:
            with self.subTest(title=title):
                assert is_relevant_title(title) is True
                assert classify_title(title) is Section.GOVERNMENT

    def test_prime_minister_civilian_policy_news_is_rejected(self) -> None:
        titles = [
            "국무총리, 민법 시행령 개정안 국무회의 의결",
            "국무총리, 개인정보 기본법 업무보고",
            "국무총리, 국민참여 국정과제 발표",
        ]

        for title in titles:
            with self.subTest(title=title):
                assert is_relevant_title(title) is False
                assert classify_title(title) is not Section.GOVERNMENT
