import pytest

from dapa_morning_brief.article_classification import classify_title
from dapa_morning_brief.models import Section


@pytest.mark.parametrize(
    "title",
    [
        "軍 보유한 지뢰 탐지·제거 장비는 뭐가 있나[이현호의 방산!톡]",
        "우리 군 보유한 지뢰 제거 장비, 어떤 종류가 있나",
        "육군 지뢰 탐지 장비의 제원과 성능은",
    ],
)
def test_military_equipment_overview_is_weapon_system(title: str) -> None:
    # Given
    description = "한국 군이 운용하는 K600과 지뢰 탐지기의 기능을 소개했다."
    # When
    section = classify_title(title, description=description, source="서울경제")
    # Then
    assert section is Section.WEAPON_SYSTEM


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("軍 보유 장비 조달제도 개편…어떤 변화 있나", Section.POLICY),
        ("현대로템, K600 장비 사업 확대…종합 방산 도약", Section.EXPORT_BUSINESS),
        ("미국 육군 보유 장비는 어떤 종류가 있나", None),
        ("민간 광산의 지뢰 탐지·제거 장비는 뭐가 있나", None),
    ],
)
def test_equipment_overview_keeps_scope_and_business_boundaries(
    title: str, expected: Section | None
) -> None:
    # Given
    description = "보유 장비 현황을 소개했다."
    # When
    section = classify_title(title, description=description, source="서울경제")
    # Then
    assert section is expected
