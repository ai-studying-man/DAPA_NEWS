from __future__ import annotations

from unittest import TestCase

from dapa_morning_brief.collector import classify_title, is_relevant_title
from dapa_morning_brief.models import Section
from dapa_morning_brief.sources import SECTION_QUERIES


class CollectorTest(TestCase):
    def test_is_relevant_title_rejects_non_defense_false_positives(self) -> None:
        # Given
        non_defense_titles = [
            "작성권 유리관리소, 환경지킴 캠페인 작업방제 실시",
            "2026년 정보통신산업(ICT) 수출 동향",
        ]

        # When
        results = [is_relevant_title(title) for title in non_defense_titles]

        # Then
        assert results == [False, False]

    def test_classify_title_detects_weapon_system_when_defense_terms_exist(
        self,
    ) -> None:
        # Given
        title = "KF-21 후속양산 계획 구체화"

        # When
        section = classify_title(title)

        # Then
        assert section is Section.WEAPON_SYSTEM

    def test_classify_title_detects_current_government_news(self) -> None:
        # Given
        title = "이재명 대통령, 자주국방과 방산수출 확대 필요성 언급"

        # When
        section = classify_title(title)

        # Then
        assert section is Section.GOVERNMENT

    def test_classify_title_detects_government_defense_policy(self) -> None:
        title = "정부, K-방산 소재·부품 공급망 안정화 대책 발표"

        section = classify_title(title)

        assert section is Section.GOVERNMENT

    def test_government_query_uses_flat_actor_context_pairs(self) -> None:
        query = SECTION_QUERIES[Section.GOVERNMENT]

        assert '"정부" 방산' in query
        assert ") (" not in query

    def test_classify_title_rejects_government_civilian_drone_news(self) -> None:
        title = "2028년 하늘길, 정부가 그린 UAM·드론 청사진"

        section = classify_title(title)

        assert section is not Section.GOVERNMENT

    def test_classify_title_excludes_former_president_news_from_government(
        self,
    ) -> None:
        # Given
        title = "윤 전 대통령 평양 무인기 침투 사건 관련 재판"

        # When
        section = classify_title(title)

        # Then
        assert section is not Section.GOVERNMENT
