import pytest

from dapa_morning_brief.article_classification import classify_title
from dapa_morning_brief.models import Section


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        (
            "한국 공군기지 교신 도청하다 붙잡힌 중국인의 정체",
            Section.GOVERNMENT,
        ),
        ("국군 군사기밀 유출 혐의 간첩 기소", Section.GOVERNMENT),
        ("한국 공군기지 도청 방지 군용 무전기 개발", Section.WEAPON_SYSTEM),
    ],
)
def test_military_security_incident_is_not_equipment_development(
    title: str, expected: Section
) -> None:
    # Given
    description = "한국 군용 통신장비와 공군 무전기에 관한 소식이다."
    # When
    section = classify_title(title, description=description, source="연합뉴스")
    # Then
    assert section is expected
