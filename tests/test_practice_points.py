from __future__ import annotations

from datetime import UTC, datetime

from dapa_morning_brief.briefing import build_briefing, format_telegram_message
from dapa_morning_brief.models import Article, Section


def test_format_telegram_message_uses_article_specific_practice_points() -> None:
    # Given
    published = datetime(2026, 7, 16, tzinfo=UTC)
    briefing = build_briefing(
        [
            Article(
                title="국방규격에 민간업체 특허 반영 논란",
                url="https://example.com/patent",
                published_at=published,
                source="뉴스A",
                section=Section.POLICY,
            ),
            Article(
                title="인천 방산혁신클러스터 조성 업무협약",
                url="https://example.com/cluster",
                published_at=published,
                source="뉴스B",
                section=Section.POLICY,
            ),
            Article(
                title="신형 장비 사업 일정 공개",
                url="https://example.com/test",
                published_at=published,
                source="뉴스C",
                section=Section.POLICY,
                description="체계개발 시험평가와 성능검증 일정을 확정했다.",
            ),
            Article(
                title="개인화기 현대화법 대표발의",
                url="https://example.com/law",
                published_at=published,
                source="뉴스D",
                section=Section.POLICY,
            ),
            Article(
                title="한-인니 방산 ICT 기술동맹 전략적 파트너 협약",
                url="https://example.com/partnership",
                published_at=published,
                source="뉴스E",
                section=Section.POLICY,
            ),
            Article(
                title="방산기업 지역사회 후원·나눔 활동",
                url="https://example.com/community",
                published_at=published,
                source="뉴스F",
                section=Section.POLICY,
            ),
        ],
        max_per_section=6,
    )

    # When
    message = format_telegram_message(
        briefing,
        today=datetime(2026, 7, 16, tzinfo=UTC).date(),
    )

    # Then
    assert "국방규격·지식재산권 반영 여부와 분쟁 영향을 확인할 필요." in message
    assert "클러스터 참여기관·지원사업·지역별 추진 일정을 확인할 필요." in message
    assert "시험평가·인증 결과와 후속 양산 일정 영향을 확인할 필요." in message
    assert "법안의 적용 대상·시행 시점과 기존 사업 영향 여부를 확인할 필요." in message
    assert "국가·기업 간 협력 범위와 공동개발·인증·수출 연계를 확인할 필요." in message
    assert "기업 사회공헌 정보의 포함 필요성을 재확인할 필요." in message
