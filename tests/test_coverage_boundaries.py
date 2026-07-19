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

    def test_non_current_defense_leader_context_is_rejected(self) -> None:
        title = "전격 해임된 '드론 천재' 국방장관, 시위대 거리로"

        assert is_relevant_title(title) is False
        assert classify_title(title) is not Section.GOVERNMENT

    def test_non_defense_government_narrative_is_rejected(self) -> None:
        title = "정부는 민법 시행령을 의결했다"

        assert is_relevant_title(title) is False
        assert classify_title(title) is not Section.GOVERNMENT

    def test_president_hanja_alias_with_work_report_is_government(self) -> None:
        title = "李 '여기에 실제 인물 몇 명?'…AI 영상까지 등장한 업무보고"

        assert is_relevant_title(title) is True
        assert classify_title(title) is Section.GOVERNMENT

    def test_former_and_candidate_defense_leaders_are_not_current(self) -> None:
        titles = (
            "국방장관 출신 정치인, 드론 정책 비판",
            "합참의장 후보자, KF-21 전력화 견해 밝혀",
        )

        for title in titles:
            with self.subTest(title=title):
                assert classify_title(title) is not Section.GOVERNMENT

    def test_civilian_company_and_event_news_is_rejected(self) -> None:
        titles = [
            "현대로템, 피지컬 AI 앞세워 글로벌 철도차량 자율주행",
            "현대로템, 철도차량용 ADAS 개발…대만 수출 정조준",
            "K-조선, 2분기 영업익 2조원대 전망",
            "전력난 AI 데이터센터…K-조선 바다 위 팹 추진",
            "수원시, 대한민국 드론·UAM 박람회 참가",
            "진천군 드론 방제로 농가 부담 덜어준다",
            "조정받은 K방산, 하반기 주가 반등 기대감",
            "상반기 치솟은 방산주, 이젠 코스피 밑돌아",
            "제이에스링크, 방산 공급망 수혜 기대",
            "대한항공, 드론 물류 수출 확대",
            "김 군, AI 드론 대회 우승",
        ]

        for title in titles:
            with self.subTest(title=title):
                assert is_relevant_title(title) is False

    def test_defense_export_and_domestic_contract_split(self) -> None:
        expectations = {
            "우크라 실전 데이터 AI 드론돔 수출…K-방산 시험대": (
                Section.EXPORT_BUSINESS
            ),
            "방사청, KDDX 7월 말 계약 추진…한화오션 우선협상": (Section.WEAPON_SYSTEM),
            "KAI, 인도네시아에 T-50i 6대 최종 인도 완료": (Section.EXPORT_BUSINESS),
            "KAI, 인도네시아에 T-50i 고등훈련기 6대 최종 납품 완료": (
                Section.EXPORT_BUSINESS
            ),
            "KAI, 인도네시아에 T-50 6대 납품…22대 공급": (Section.EXPORT_BUSINESS),
            "KAI, 인니에 T-50i 고등훈련기 6대 최종 납품 완료": (
                Section.EXPORT_BUSINESS
            ),
            "T-50i 인도네시아 수출 본격화": Section.EXPORT_BUSINESS,
            "KAI, 미국에 T-50 훈련기 수출 계약": Section.EXPORT_BUSINESS,
            "한화 필리조선소, 美 미사일 추적선 수주…방산조선 보폭 확대": (
                Section.EXPORT_BUSINESS
            ),
            "K2 전차 국내 납품 완료": Section.WEAPON_SYSTEM,
        }

        for title, section in expectations.items():
            with self.subTest(title=title):
                assert is_relevant_title(title) is True
                assert classify_title(title) is section

    def test_standalone_military_subject_is_relevant(self) -> None:
        title = "군, AI 기반 드론 전력화 추진"

        assert is_relevant_title(title) is True
