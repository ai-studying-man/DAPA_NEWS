import pytest

from dapa_morning_brief.models import Section
from dapa_morning_brief.rss_parser import classify_title, is_relevant_article


@pytest.mark.parametrize(
    ("title", "section"),
    [
        ("보라매 초도양산 착수", Section.WEAPON_SYSTEM),
        ("KF21 시험평가 완료", Section.WEAPON_SYSTEM),
        ("ROTEM, K2 전차 폴란드 수출 계약", Section.EXPORT_BUSINESS),
        ("LIG D&A, 국방부 유도무기 성능개량 계약 체결", Section.WEAPON_SYSTEM),
        ("한화 오션, 한국 해군 잠수함 건조 착수", Section.WEAPON_SYSTEM),
        ("한화 시스템, 군용 통신장비 부품국산화 사업 추진", Section.POLICY),
        ("방산기업 영업이익 증가…천궁 양산 계약 체결", Section.WEAPON_SYSTEM),
        ("국방부, 소요결정 제도 개선", Section.POLICY),
    ],
)
def test_confirmed_alias_and_context_are_collected(
    title: str, section: Section
) -> None:
    # Given: topical metadata from a domestic newspaper.
    source = "연합뉴스"
    # When
    actual = (
        is_relevant_article(title, "", source),
        classify_title(title, source=source),
    )
    # Then
    assert actual == (True, section)


@pytest.mark.parametrize(
    "title",
    [
        "러시아 T-50 전투기 시험비행",
        "일본 F-35A 추가 도입",
        "K21A99 신제품 출시",
        "ROTEM 철도차량 해외 수주",
        "LIG 보험 영업이익 증가",
        "방사청 언급에 방산주 목표주가 상승",
        "한화시스템 방산 영업이익 급증",
        "LIG D&A 고문 영입으로 방산 경쟁력 강화",
    ],
)
def test_ambiguous_entities_and_financial_only_news_are_rejected(title: str) -> None:
    # Given / When
    relevant = is_relevant_article(title, "", "연합뉴스")
    # Then
    assert relevant is False


def test_official_publisher_does_not_override_weapon_topic() -> None:
    # Given
    title = "수직이착륙 무인항공기 국내 개발 착수"
    # When
    result = (
        is_relevant_article(title, "", "국방일보"),
        classify_title(title, source="국방일보"),
    )
    # Then
    assert result == (True, Section.WEAPON_SYSTEM)


def test_official_publisher_alone_does_not_make_article_relevant() -> None:
    # Given / When
    relevant = is_relevant_article("주말 문화 행사 개최", "", "국방일보")
    # Then
    assert relevant is False
