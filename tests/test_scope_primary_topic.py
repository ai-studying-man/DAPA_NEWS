import pytest

from dapa_morning_brief.article_classification import (
    classify_title,
    is_relevant_article,
)
from dapa_morning_brief.models import Section
from dapa_morning_brief.topic_boundaries import is_incidental_civic_agenda


@pytest.mark.parametrize("country", ["튀르키예", "터키", "브라질", "인도네시아"])
def test_rejects_foreign_domestic_weapon_without_korean_link(country: str) -> None:
    # Given
    title = f"국산 훈련기 첫 납품, {country} 공군 전력 강화"
    description = "자국 항공업체가 개발한 국산 훈련기를 공군에 공급했다."
    # When
    relevant = is_relevant_article(title, description, "방산신문")
    # Then
    assert relevant is False


@pytest.mark.parametrize(
    "title",
    [
        "국산 훈련기 휘르쿠시-II, 튀르키예 공군 첫 편입",
        "튀르키예 국산 전투기 개발, 공군 전력 강화",
    ],
)
def test_foreign_domestic_weapon_has_no_category(title: str) -> None:
    # Given
    description = "자국 항공산업의 국산 전투기 개발과 방산 수출 확대 계획이다."
    # When
    section = classify_title(title, description=description)
    # Then
    assert section is None


@pytest.mark.parametrize(
    "title",
    [
        "튀르키예 공군, 한국 훈련기 도입 계약",
        "튀르키예 공군, KAI 훈련기 구매 협력",
        "방사청, 튀르키예 공군용 엔진 도입 검토",
        "방사청, 튀르키예산 엔진 구매 추진",
    ],
)
def test_preserves_explicit_korean_supply_and_acquisition(title: str) -> None:
    # Given
    description = (
        "한국 방위사업청과 항공업체가 방산 수출 계약과 "
        "군용 항공기 구매 협력을 논의했다."
    )
    # When
    relevant = is_relevant_article(title, description, "방산신문")
    # Then
    assert relevant is True


def test_rejects_defense_as_one_item_in_civic_budget_agenda() -> None:
    # Given
    title = '"골목경제부터 방산·AI·푸드테크까지"…시청, 도의원들과 예산 확보 맞손'
    description = (
        "지자체는 내년도 예산 확보를 논의했다. 전통시장 활성화와 철도망 구축, "
        "박물관 건립과 출산 지원, 방산·AI 특화 공유공장 구축을 건의했다."
    )
    # When
    relevant = is_relevant_article(title, description, "지역신문")
    # Then
    assert relevant is False
    assert classify_title(title, description=description) is None


def test_preserves_dedicated_defense_cluster_budget() -> None:
    # Given
    title = "시청, 방산혁신클러스터 구축 예산 확보"
    description = (
        "방위사업청과 방산기업 시험평가 시설 구축을 추진한다. "
        "방산 부품 국산화 예산을 지원한다. 전통시장과 철도 사업은 별도 논의한다."
    )
    # When
    relevant = is_relevant_article(title, description, "지역신문")
    # Then
    assert relevant is True


def test_detects_incidental_defense_from_body_without_mixed_title() -> None:
    # Given
    title = "시청, 도의원들과 내년도 국비 확보 협의"
    body = (
        "전통시장 활성화 예산과 보육 지원, 철도망 확충 사업을 논의했다. "
        "방산 특화 공유공장도 지원 대상에 포함됐다."
    )
    # When
    incidental = is_incidental_civic_agenda(title, body)
    # Then
    assert incidental is True


@pytest.mark.parametrize(
    "title",
    [
        "사막서 등장한 천무…사우디 군 홍보 영상 화제",
        "폴란드 군 K9 자주포 홍보영상 공개",
        "루마니아 군 K9 자주포 현지 운용 본격화",
    ],
)
def test_foreign_use_of_korean_weapons_is_export_business(title: str) -> None:
    # Given
    description = "도입한 한국 무기체계의 실제 운용 모습을 공개했다."
    # When
    section = classify_title(title, description=description)
    # Then
    assert section is Section.EXPORT_BUSINESS


@pytest.mark.parametrize(
    "title",
    [
        "방사청, K2 전차 폴란드 현지 운용 시험평가 착수",
        "K9 자주포 성능개량…폴란드 현지 운용 시험",
        "KF-21 체계개발 시험비행, 호주 현지 운용 검증",
    ],
)
def test_foreign_test_site_does_not_turn_development_into_export(title: str) -> None:
    # Given
    description = "국내 전력화를 위한 개발 시험을 진행했다."
    # When
    section = classify_title(title, description=description)
    # Then
    assert section is Section.WEAPON_SYSTEM


def test_civilian_foreign_video_does_not_get_export_category() -> None:
    # Given
    title = "사우디 관광 홍보영상 공개"
    description = "한국 관광객을 위한 여행 코스를 소개했다."
    # When
    section = classify_title(title, description=description)
    # Then
    assert section is None


@pytest.mark.parametrize(
    "title",
    [
        "NIA-국방부, 700만 국방 관계자가 이용하는 원스톱 국방 플랫폼 장병e음 성과공유",
        "장병이음, 군 행정 서비스 정식 개통",
        "장병이(e)음 복지 서비스 이용 확대",
    ],
)
def test_soldier_administration_service_is_government_news(title: str) -> None:
    # Given
    description = "국방부의 통합 행정 플랫폼이 장병 복지 서비스를 제공한다."
    # When
    section = classify_title(title, description=description)
    # Then
    assert section is Section.GOVERNMENT


@pytest.mark.parametrize(
    "title",
    [
        "국방부, 장병e음 서비스 조달 계약 체결",
        "장병이음 플랫폼 보안 결함 논란",
        "장병이(e)음 AI 서비스 보안 취약점 발견",
    ],
)
def test_soldier_platform_procurement_and_security_remain_policy(title: str) -> None:
    # Given
    description = "국방부의 통합 행정 플랫폼 운영 현황을 조사했다."
    # When
    section = classify_title(title, description=description)
    # Then
    assert section is Section.POLICY
