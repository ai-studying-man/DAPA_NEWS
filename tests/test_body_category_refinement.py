from datetime import UTC, datetime

import pytest

from dapa_morning_brief.briefing import build_briefing
from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.models import Article, Section


@pytest.mark.parametrize(
    ("title", "body", "expected"),
    [
        (
            "예정보다 빨리 온 한국 K9…루마니아 첫 수송대열에 구원투수도 [밀리터리+]",
            "한화에어로스페이스의 K9 자주포 수출 물량이 루마니아에 조기 인도됐다.",
            Section.EXPORT_BUSINESS,
        ),
        (
            "한국 K2 폴란드 현지 도착…첫 수송 물량 공개",
            "현대로템의 K2 전차가 폴란드 수출 계약에 따라 현지 항구에 도착했다.",
            Section.EXPORT_BUSINESS,
        ),
        (
            "국내 K9 자주포 성능개량 시험 완료",
            "국내 자주포의 개량 시험이 끝났다. 배경으로 루마니아 수출 성과도 소개했다.",
            Section.WEAPON_SYSTEM,
        ),
        (
            "한국 K9 루마니아 훈련 첫 수송",
            "K9 자주포가 연합훈련 참가 목적으로 이동했다. 수출 계약의 인도는 아니다.",
            Section.WEAPON_SYSTEM,
        ),
        (
            "예정보다 빨리 온 한국 K9…루마니아 첫 수송대열에 구원투수도",
            "",
            Section.WEAPON_SYSTEM,
        ),
        (
            "[이 시각 세계] 사막서 여유롭게 차 한 잔‥뒤편엔 천무",
            (
                "사막에서 차를 마시는 남성들 뒤로 한국산 천무가 등장한다. "
                "사우디아라비아 군 당국이 공개한 홍보 영상이다."
            ),
            Section.EXPORT_BUSINESS,
        ),
        (
            "천무 성능개량 시험 완료",
            (
                "국내 전력화를 위한 시험을 마쳤다. "
                "배경으로 사우디 군 천무 홍보 영상도 소개했다."
            ),
            Section.WEAPON_SYSTEM,
        ),
        (
            "천무 새 장비 공개",
            (
                "국내 전력화를 위한 천무 성능개량 시험 결과를 공개했다. "
                "배경으로 사우디 군 천무 홍보 영상도 소개했다."
            ),
            Section.WEAPON_SYSTEM,
        ),
        (
            "천무 운용 현황 공개",
            "우리 군 부대의 교육 계획을 소개한다. " * 40
            + "사우디 군 천무 홍보 영상은 과거 사례다.",
            Section.WEAPON_SYSTEM,
        ),
    ],
)
def test_body_refines_category_only_for_headline_led_overseas_delivery(
    title: str, body: str, expected: Section
) -> None:
    # Given
    article = Article(
        title=title,
        url="https://example.com/delivery",
        published_at=datetime(2026, 9, 29, tzinfo=UTC),
        source="뉴스",
        section=Section.WEAPON_SYSTEM,
    )
    extracted = ArticleBody(
        article_url=article.url, title=title, source=article.source, body=body
    )
    # When
    result = build_briefing((article,), max_per_section=5, article_bodies=(extracted,))
    # Then
    assert [item.url for item in result.sections[expected]] == [article.url]
    assert result.sections[expected][0].section is expected
    assert sum(map(len, result.sections.values())) == 1
    assert article.section is Section.WEAPON_SYSTEM


def test_refined_article_is_rebucketed_before_section_quotas() -> None:
    # Given
    titles = (
        "KF-21 전투기 시험비행",
        "K2 전차 성능개량",
        "잠수함 신형 소나 개발",
        "천궁 요격체계 시험",
        "대형 수송기 국내 양산",
        "한화 해외 공장 건설",
        "KAI 멕시코 협력",
        "LIG 유럽 지사 개소",
        "현대로템 해외 정비센터",
        "풍산 탄약 공급 계약",
    )
    articles = [
        Article(
            title=title,
            url=f"https://example.com/{index}",
            published_at=datetime(2026, 9, 28, tzinfo=UTC),
            source="뉴스",
            section=Section.WEAPON_SYSTEM if index < 5 else Section.EXPORT_BUSINESS,
        )
        for index, title in enumerate(titles)
    ]
    delivery = Article(
        title="한국 K9 루마니아 첫 수송대열",
        url="https://example.com/delivery",
        published_at=datetime(2026, 9, 29, tzinfo=UTC),
        source="뉴스",
        section=Section.WEAPON_SYSTEM,
    )
    body = ArticleBody(
        article_url=delivery.url,
        title=delivery.title,
        source=delivery.source,
        body="K9 자주포 수출 물량이 루마니아에 도착했다.",
    )
    # When
    result = build_briefing(
        (*articles, delivery), max_per_section=5, article_bodies=(body,)
    )
    # Then
    assert len(result.sections[Section.WEAPON_SYSTEM]) == 5
    assert len(result.sections[Section.EXPORT_BUSINESS]) == 5
    assert delivery.url in {
        item.url for item in result.sections[Section.EXPORT_BUSINESS]
    }
