import pytest

from dapa_morning_brief.article_classification import classify_title
from dapa_morning_brief.models import Section


@pytest.mark.parametrize(
    "title",
    [
        "무인화·국산화·현지화…한화, 방산 체질 전환 속도",
        "KF-21 넘어 AI 전투 체계로…KAI, 미래 방산 정조준",
        "전차·철도 넘어 항공우주로…현대로템, 종합 방산社로 체급 키운다",
        "LIG넥스원, 무인체계 사업 다각화로 방산 성장 모색",
    ],
)
def test_company_wide_strategy_is_business_news(title: str) -> None:
    # Given
    description = "방산기업이 성장 전략과 사업 포트폴리오를 소개했다."
    # When
    section = classify_title(title, description=description)
    # Then
    assert section is Section.EXPORT_BUSINESS


@pytest.mark.parametrize(
    "title",
    [
        "한화에어로스페이스, K9 자주포 성능개량 착수",
        "KAI, KF-21 시험비행 성공…미래 방산 기술 확보",
        "현대로템, K2 전차 시험평가 완료",
        "LIG넥스원, 천궁 체계개발 착수",
    ],
)
def test_specific_weapon_lifecycle_remains_weapon_news(title: str) -> None:
    # Given
    description = "국내 전력화를 위한 무기체계 개발 성과를 공개했다."
    # When
    section = classify_title(title, description=description)
    # Then
    assert section is Section.WEAPON_SYSTEM


def test_generic_corporate_strategy_without_defense_is_not_business_news() -> None:
    # Given
    title = "한화, 유통 사업 다각화로 체질 전환"
    # When
    section = classify_title(title)
    # Then
    assert section is None
