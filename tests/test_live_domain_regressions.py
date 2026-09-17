import pytest

from dapa_morning_brief.models import Section
from dapa_morning_brief.rss_parser import classify_title, is_relevant_article


@pytest.mark.parametrize(
    ("title", "description", "source"),
    [
        ('美 국방부 CTO "AI 기업 지분 인수 반대"…정부 개입에 선 긋기', "", "연합뉴스"),
        ("美 공군, VIP 수송에 737 MAX 도입…첫 군용 버전", "", "연합뉴스"),
        (
            "킨티엔 궁전 복원을 위한 과학적 기반 마련",
            "선행연구와 국내 복원 사례 분석",
            "vietnam.vn",
        ),
        ("양구 출신 전 방위사업청 본부장, 연구자문위원 선임", "", "강원일보"),
        ("방산기업, 사외이사 임명으로 경쟁력 강화", "", "연합뉴스"),
    ],
)
def test_live_irrelevant_candidates_are_excluded(
    title: str, description: str, source: str
) -> None:
    # Given / When
    relevant = is_relevant_article(title, description, source)
    # Then
    assert not relevant


def test_weapon_development_action_beats_generic_technology_policy() -> None:
    # Given
    title = "軍, 2.16조 수직이착륙 정찰무인기 국내개발… K-방산 무인체계 넓힌다"
    description = "국방예산을 투입해 체계개발을 추진한다."
    # When
    actual = classify_title(title, description=description, source="연합뉴스")
    # Then
    assert actual is Section.WEAPON_SYSTEM


def test_presidential_defense_appointment_remains_major_government_news() -> None:
    # Given / When
    actual = is_relevant_article("대통령, 신임 국방부 장관 임명", "", "연합뉴스")
    # Then
    assert actual


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ('"용산공원 미군 반환기지·방사청 부지 검토…2만8천 호 가능"', False),
        ("방사청 이전 부지, 아파트 주택 공급 재개발 추진", False),
        ("방사청, 군 숙소 시설 건설 계약 체결", True),
        ("방사청 이전 부지 개발 검토…무기체계 시험평가 시설 확보", True),
    ],
)
def test_agency_site_housing_requires_acquisition_fact(
    title: str, expected: bool
) -> None:
    # Given / When
    relevant = is_relevant_article(title, "", "연합뉴스")
    # Then
    assert relevant is expected


@pytest.mark.parametrize(
    ("title", "description"),
    [
        (
            "인텔리빅스, 증권신고서 제출...코스닥 상장 절차 돌입",
            "방위사업청 등을 고객으로 두고 있으며 무기체계 시험평가 사업도 수행했다.",
        ),
        (
            "스트림비젼, AI 실시간 자막·방송 모니터링 기능 강화",
            "방사청과 국방부 등에 공급한 경험을 바탕으로 방송 기능을 개선했다.",
        ),
        (
            "[Who Is ?] 김동관 한화그룹 수석부회장",
            " ".join(
                (
                    "한화오션은 2026년 7월31일 방위사업청과",
                    "KDDX 상세설계·선도함 건조 계약을 체결했다.",
                )
            ),
        ),
    ],
)
def test_incidental_defense_customer_does_not_admit_unrelated_headline(
    title: str,
    description: str,
) -> None:
    # Given / When
    relevant = is_relevant_article(title, description, "국내언론")
    # Then
    assert not relevant


def test_public_procurement_topic_does_not_become_weapon_from_example() -> None:
    # Given
    title = "공공사업 대참제 빗장 풀리는데…중견 IT업계 심의·입찰 안전장치부터"
    description = (
        "현재 방위사업청이 발주한 합동지휘통제체계(KJCCS) "
        "경미한 성능개량 사업도 비슷한 우려를 낳고 있다."
    )
    # When
    actual = (
        is_relevant_article(title, description, "디지털데일리"),
        classify_title(title, description=description, source="디지털데일리"),
    )
    # Then
    assert actual == (True, Section.POLICY)


def test_acquisition_headline_can_use_description_to_identify_agency() -> None:
    # Given / When
    relevant = is_relevant_article(
        "획득제도 개선 설명회 개최",
        "방위사업청이 제도 개선 내용을 발표했다.",
        "연합뉴스",
    )
    # Then
    assert relevant
