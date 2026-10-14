from datetime import UTC, datetime

import pytest

from dapa_morning_brief.article_selection_review import review_selection
from dapa_morning_brief.briefing import build_briefing
from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.models import Article, Section


@pytest.mark.parametrize(
    ("title", "body", "original"),
    [
        (
            "[단독] 미 국방차관, 주한미군 준비태세 평가와 본토 방어 우선 전략",
            "미 국방차관은 주한미군 준비태세와 가족 복지 정책을 평가했다.",
            Section.WEAPON_SYSTEM,
        ),
        (
            "국회 국방위, '北 지뢰도발 규탄 결의안' 與 주도 채택",
            " ".join(
                (
                    "국회 국방위원회는 북한 지뢰도발 규탄 결의안을 채택했다.",
                    "여야는 표결을 두고 대립했다.",
                    "결의안은 부상 장병 치료와 진상규명을 요구했다. " * 10,
                    "한편 LIG넥스원 관계자 증인 채택도 논의했다.",
                )
            ),
            Section.EXPORT_BUSINESS,
        ),
    ],
)
def test_public_policy_is_rebucketed_when_main_subject_is_confirmed(
    title: str, body: str, original: Section
) -> None:
    # Given
    article = Article(
        title,
        "https://example.com/policy",
        datetime(2026, 10, 15, tzinfo=UTC),
        "뉴스",
        original,
    )
    # When
    result = review_selection(article, body)
    # Then
    assert result.article is not None
    assert result.article.section is Section.GOVERNMENT
    assert result.status.value == "accepted"


@pytest.mark.parametrize(
    ("title", "body", "section"),
    [
        (
            "국방부, 한국형 신형 요격체계 개발 시험 완료",
            "국내 독자 기술로 개발한 요격 무기체계 시험이 완료됐다.",
            Section.WEAPON_SYSTEM,
        ),
        (
            "LIG D&A, 美 파이어호크와 비궁 추진체 개발 협력",
            "LIG D&A는 미국 파이어호크와 비궁 로켓 추진체 개발 협약을 체결했다.",
            Section.EXPORT_BUSINESS,
        ),
        (
            "육군 무전기 290대 방치…구매사업 조정 부실",
            "육군 TMMR 구매사업에서 연결선이 짧아 운용하지 못하는 문제가 드러났다.",
            Section.POLICY,
        ),
        (
            "국회 국방위, K9 성능개량 시험 결과 보고",
            "국내 K9 자주포 성능개량 시험의 개선 제원을 보고했다.",
            Section.WEAPON_SYSTEM,
        ),
        (
            "현장 점검 결과 공유",
            "담당자들은 현장 점검 결과를 공유했다.",
            Section.POLICY,
        ),
    ],
)
def test_normal_article_survives_when_primary_government_action_is_absent(
    title: str, body: str, section: Section
) -> None:
    # Given
    article = Article(
        title,
        "https://example.com/normal",
        datetime(2026, 10, 15, tzinfo=UTC),
        "뉴스",
        section,
    )
    # When
    result = review_selection(article, body)
    # Then
    assert result.article is not None
    assert result.article.section is section


def test_government_reclassification_precedes_final_section_quota() -> None:
    # Given
    article = Article(
        "국회 국방위, 북한 지뢰도발 규탄 결의안 채택",
        "https://example.com/resolution",
        datetime(2026, 10, 15, tzinfo=UTC),
        "뉴스",
        Section.EXPORT_BUSINESS,
    )
    body = ArticleBody(
        article.url,
        article.title,
        article.source,
        "국회 국방위원회는 북한 지뢰도발 규탄 결의안을 채택했다.",
    )
    # When
    result = build_briefing((article,), max_per_section=5, article_bodies=(body,))
    # Then
    assert [item.url for item in result.sections[Section.GOVERNMENT]] == [article.url]
    assert sum(map(len, result.sections.values())) == 1
