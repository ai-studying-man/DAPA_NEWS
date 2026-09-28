from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from dapa_morning_brief.models import Article, Section
from dapa_morning_brief.rss_parser import classify_title, is_relevant_article
from dapa_morning_brief.story_deduplication import are_same_articles


@pytest.mark.parametrize(
    "title",
    [
        "[Game & Now] 공군서 TFT 대회, 결승 8명 '포상휴가'…SOOP ASL 4강 경쟁",
        "한국항공우주 13만원대 상승…KF-21·FA-50 사업에 시선",
        "순천제일대 취업처 다변화…반도체·자동차·방산까지 진출",
        "파주시, 한국국방연구원 유치 총력",
        "산업계 다양한 의견 소개",
    ],
)
def test_preview_noise_is_rejected(title: str) -> None:
    # Given / When
    relevant = is_relevant_article(
        title,
        "한국의 국방예산과 방산 수출에 관한 배경을 소개했다.",
        "연합뉴스",
    )
    # Then
    assert not relevant


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        (
            "한화, K9·천무도 무인화…로봇 전장으로 방산 영토 넓힌다",
            Section.WEAPON_SYSTEM,
        ),
        (
            "KAI, 멕시코 항공우주산업 협력 확대…FA-50 중남미 진출 교두보 마련",
            Section.EXPORT_BUSINESS,
        ),
        (
            '김종출 KAI 대표 "멕시코 기반으로 FA-50 중미 시장 진출 추진"',
            Section.EXPORT_BUSINESS,
        ),
        (
            "한화에어로, 루마니아에 6개월 앞당겨 K9 자주포 조기 인도",
            Section.EXPORT_BUSINESS,
        ),
        ("국방 플랫폼 장병이음, 국방 AI 에이전트 시대 연다", Section.GOVERNMENT),
        ("국제표준부터 정보기술까지…K방산 국제 경쟁력 강화", Section.POLICY),
        (
            "[어바웃 현대로템] 현지생산 폴란드 K2, 수익성 확보 방안은",
            Section.EXPORT_BUSINESS,
        ),
        ("NIA·국방부, 장병e음 10월 정식 서비스…AI 챗봇 탑재", Section.GOVERNMENT),
        (
            "KT, 나토 통신 표준화 프로젝트 합류…차세대 군용 5G·6G 규격 논의",
            Section.POLICY,
        ),
    ],
)
def test_live_headlines_follow_event_not_technology_keyword(
    title: str,
    expected: Section,
) -> None:
    # Given / When
    section = classify_title(title, source="연합뉴스")
    # Then
    assert section is expected


@pytest.mark.parametrize(
    ("left_title", "right_title"),
    [
        (
            "KAI, 멕시코 항공우주산업 협력 확대…FA-50 중남미 진출 교두보 마련",
            '김종출 KAI 대표 "멕시코 기반으로 FA-50 중미 시장 진출 추진"',
        ),
        (
            "KAI, 멕시코 항공우주산업협회와 MOU…중남미 사업 확대 모색",
            "KAI Targets Mexico's Aerospace Supply Chain with FA-50 and Local Partners",
        ),
        (
            "군 생활, 이제 AI에 묻는다…장병용 AI 10월 가동",
            "국방 플랫폼 장병이음, 국방 AI 에이전트 시대 연다",
        ),
        (
            "육군·대전시, 국방 AX 협력체계 구축",
            "대전 방산기업, 육군 데이터로 AI 개발한다…옛 대덕경찰서 실증 거점",
        ),
        (
            "NIA·국방부, 장병e음 10월 정식 서비스…AI 챗봇 탑재",
            "46개 군 서비스 한곳에…장병e음 내달 AI 고도화",
        ),
        (
            "NIA·국방부, 장병e음 10월 정식 서비스…AI 챗봇 탑재",
            "[AI프리즘] 증명서 2주→1\u223c2분…장병e음에 AI 비서 들어온다",
        ),
    ],
)
def test_live_event_paraphrases_are_one_story(
    left_title: str, right_title: str
) -> None:
    # Given
    left = Article(
        title=left_title,
        url="https://example.com/one",
        published_at=datetime(2026, 9, 28, tzinfo=UTC),
        source="연합뉴스",
        section=Section.POLICY,
        description=(
            "멕시코 항공우주산업협회(FEMIA)와 항공우주 협력 MOU를 체결했다."
            if "멕시코" in left_title
            else ""
        ),
    )
    right = replace(left, title=right_title, url="https://example.com/two")
    # When
    same = are_same_articles(left, right)
    # Then
    assert same


def test_recurring_event_is_not_merged_across_weeks() -> None:
    # Given
    left = Article(
        title="한화 군인 가족 초청 힐링데이",
        url="https://example.com/first",
        published_at=datetime(2026, 9, 1, tzinfo=UTC),
        source="연합뉴스",
        section=Section.EXPORT_BUSINESS,
    )
    right = replace(
        left,
        url="https://example.com/next",
        published_at=left.published_at + timedelta(days=7),
    )
    # When
    same = are_same_articles(left, right)
    # Then
    assert not same


@pytest.mark.parametrize(
    ("left_title", "right_title"),
    [
        ("KAI 멕시코 항공정비 현지화 추진", "한국항공우주 멕시코 위성영상 교두보 확보"),
        ("장병용 AI 보안 취약점 발견", "장병이음 AI 상담 서비스 확대"),
    ],
)
def test_shared_actor_or_service_does_not_mean_same_event(
    left_title: str,
    right_title: str,
) -> None:
    # Given
    left = Article(
        title=left_title,
        url="https://example.com/left",
        published_at=datetime(2026, 9, 28, tzinfo=UTC),
        source="연합뉴스",
        section=Section.POLICY,
    )
    right = replace(left, title=right_title, url="https://example.com/right")
    # When / Then
    assert not are_same_articles(left, right)


def test_soldier_ai_company_development_is_not_government_action() -> None:
    # Given / When
    section = classify_title("한국 기업, 장병용 AI 보안 솔루션 개발", source="연합뉴스")
    # Then
    assert section is not Section.GOVERNMENT


def test_foreign_procurement_needs_korean_target_in_headline() -> None:
    # Given / When
    relevant = is_relevant_article(
        "미국 육군 전차 도입 검토",
        "한화의 K9 수출 실적을 배경으로 소개했다.",
        "연합뉴스",
    )
    # Then
    assert not relevant


def test_service_alias_and_cloud_announcement_are_same_launch() -> None:
    # Given
    left = Article(
        title="NIA·국방부, 장병e음 10월 정식 서비스…AI 챗봇 탑재",
        url="https://example.com/alias",
        published_at=datetime(2026, 9, 28, tzinfo=UTC),
        source="연합뉴스",
        section=Section.GOVERNMENT,
    )
    right = replace(
        left,
        title="국방부 최초 민간 클라우드 도입 시스템 순항",
        url="https://example.com/cloud",
    )
    # When
    same = are_same_articles(
        left,
        right,
        right_body="국방부 장병이음 AI 서비스가 10월 정식 서비스를 시작한다.",
    )
    # Then
    assert same
