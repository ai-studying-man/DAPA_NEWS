from __future__ import annotations

from datetime import UTC, datetime

from dapa_morning_brief.briefing import build_briefing, format_telegram_message
from dapa_morning_brief.models import Article, PracticePoint, Section


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
    assert "국방규격·지식재산권 반영 및 분쟁 영향 확인" in message
    assert "클러스터 참여기관·지원사업·지역별 추진 일정 확인" in message
    assert "시험평가·인증 결과 및 후속 양산 일정 영향 확인" in message
    assert "법안 적용 대상·시행 시점 및 기존 사업 영향 확인" in message
    assert "국가·기업 간 협력 범위 및 공동개발·인증·수출 연계 확인" in message
    assert "방위사업 직접 관련성 및 기업 사회공헌 정보 포함 필요성 확인" in message


def test_format_telegram_message_prefers_copilot_practice_point() -> None:
    # Given
    article = Article(
        title="KF-21 후속 양산 일정 확정",
        url="https://example.com/kf21",
        published_at=datetime(2026, 8, 6, tzinfo=UTC),
        source="테스트뉴스",
        section=Section.WEAPON_SYSTEM,
    )
    briefing = build_briefing([article], max_per_section=1)
    copilot_point = PracticePoint(
        article_url=article.url,
        text="후속 양산 계약 시점 및 납품 일정 확인",
    )

    # When
    message = format_telegram_message(
        briefing,
        today=datetime(2026, 8, 6, tzinfo=UTC).date(),
        practice_points=(copilot_point,),
    )

    # Then
    assert copilot_point.text in message


def test_practice_points_are_omitted_from_government_news() -> None:
    # Given
    published = datetime(2026, 8, 6, tzinfo=UTC)
    government = Article(
        title="국방부 장병 지원대책 발표",
        url="https://example.com/government",
        published_at=published,
        source="정부뉴스",
        section=Section.GOVERNMENT,
    )
    policy = Article(
        title="방위사업청 조달제도 개선",
        url="https://example.com/policy",
        published_at=published,
        source="정책뉴스",
        section=Section.POLICY,
    )
    briefing = build_briefing([government, policy], max_per_section=1)

    # When
    message = format_telegram_message(briefing, today=published.date())

    # Then
    assert message.count("📌 실무 참고:") == 1
    assert message.index("방위사업청 조달제도 개선") < message.index("📌 실무 참고:")


def test_keyword_practice_point_ends_as_nominal_phrase() -> None:
    # Given
    published = datetime(2026, 8, 6, tzinfo=UTC)
    article = Article(
        title="AI 무인체계 운용지침 개정",
        url="https://example.com/ai-policy",
        published_at=published,
        source="정책뉴스",
        section=Section.POLICY,
    )
    briefing = build_briefing([article], max_per_section=1)

    # When
    message = format_telegram_message(briefing, today=published.date())

    # Then
    assert "📌 실무 참고: AI·무인체계 운용 보안 및 정책·규제 준수 여부 확인" in message
