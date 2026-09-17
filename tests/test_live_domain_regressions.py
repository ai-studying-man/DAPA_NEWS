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
            "한화오션은 7월 방위사업청과 KDDX 선도함 건조 계약을 체결했다.",
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


@pytest.mark.parametrize(
    ("title", "description"),
    [
        (
            "우주항공· 방산 주 일제히 날았다…나라스페이스 29%↑·켄코아 26%↑",
            "한화시스템, 현대로템 등이 상승했다.",
        ),
        (
            "유진투자증권 한화시스템 레이저 무기 천광 새 성장축…목표가 상향",
            "2024년 양산 계약 체결 후 전력화했다. 정부는 후속 사업을 추진한다.",
        ),
        (
            "2호선 구로디지털단지역 연결 GD메트로타워 770실 분양",
            "보라매 공원에서 신대방역을 거쳐 이어지는 교통망.",
        ),
        (
            "스트림비젼, AI 실시간 자막·방송 모니터링 기능 강화",
            "국방부, 한국수력원자력 등에 공급한 고객 실적을 갖췄다.",
        ),
    ],
)
def test_stock_and_civilian_headlines_cannot_use_background_defense_mentions(
    title: str,
    description: str,
) -> None:
    # Given / When
    relevant = is_relevant_article(title, description, "국내언론")
    # Then
    assert not relevant


@pytest.mark.parametrize(
    ("title", "description", "expected"),
    [
        (
            "한화시스템, EDGE그룹과 전략적 협력…UAE 합작법인 설립 검토",
            "EDGE는 UAE 정부가 설립한 방산 기업이다. 중동 수출 경쟁력을 강화한다.",
            Section.EXPORT_BUSINESS,
        ),
        (
            "한화시스템, UAE 방산기업과 현지 통합대공망 구축",
            "AI 플랫폼 공동개발 협력을 확대한다.",
            Section.EXPORT_BUSINESS,
        ),
        (
            "中 견제 나선 美 해군…韓·日 함정 도입 검토",
            "한국 방산 및 조선업계의 기회다. 충남급 호위함이 후보로 거론됐다.",
            Section.EXPORT_BUSINESS,
        ),
        (
            "NC AI, 피지컬 AI 국책사업 참여",
            "정부는 사업을 추진한다. 현대로템과 방산 분야 기술을 개발한다.",
            Section.POLICY,
        ),
    ],
)
def test_incidental_foreign_or_domestic_government_does_not_set_topic(
    title: str,
    description: str,
    expected: Section,
) -> None:
    # Given / When
    section = classify_title(title, description=description, source="국내언론")
    # Then
    assert section is expected


def test_boramae_aircraft_alias_keeps_explicit_military_context() -> None:
    # Given / When
    actual = is_relevant_article("보라매 초도양산 착수", "", "연합뉴스")
    # Then
    assert actual
