from datetime import UTC, datetime
from io import StringIO
from unittest.mock import patch

import pytest

from dapa_morning_brief.cli import main
from dapa_morning_brief.models import Article, Section


@pytest.mark.parametrize("count", [0, 1, 2, 3, 5])
@pytest.mark.parametrize("copies", [1, 2])
def test_backfill_when_section_has_fewer_than_three(count: int, copies: int) -> None:
    # Given: every other section has enough distinct articles.
    titles = {
        Section.POLICY: (
            "획득 예산 편성",
            "조달 절차 개선",
            "품질 인증 확대",
            "규격 문서 개정",
            "선행 연구 착수",
        ),
        Section.GOVERNMENT: (
            "대통령 국무회의 주재",
            "장관 부대 방문",
            "정부 업무보고 시행",
        ),
        Section.WEAPON_SYSTEM: (
            "전투기 양산 계약",
            "미사일 요격 시험",
            "잠수함 신규 배치",
        ),
        Section.EXPORT_BUSINESS: (
            "유럽 수출 협상",
            "기업 해외 공장 설립",
            "중동 납품 완료",
        ),
    }
    daily = [
        Article(
            title=title,
            url=f"https://example.com/{section.name}/{index}",
            published_at=datetime(2026, 9, 17, tzinfo=UTC),
            source="테스트뉴스",
            section=section,
        )
        for section in Section
        for index, title in enumerate(
            titles[section][: count if section == Section.POLICY else 3]
        )
    ]
    fallback = Article(
        title="방위사업청 조달 제도 개편 발표",
        url="https://example.com/backfill",
        published_at=datetime(2026, 9, 16, tzinfo=UTC),
        source="테스트뉴스",
        section=Section.POLICY,
    )
    output = StringIO()
    # When: run the real CLI formatting and selection without external delivery.
    with (
        patch(
            "dapa_morning_brief.cli.collect_articles",
            side_effect=[daily * copies, [fallback]],
        ) as collect,
        patch("dapa_morning_brief.cli.collect_weather_forecasts", return_value=()),
        patch("sys.stdout", output),
    ):
        result = main(["--dry-run"])
    # Then: the boundary is three, and supplementary content reaches the output.
    assert result == 0
    assert collect.call_count == (2 if count < 3 else 1)
    assert (fallback.url in output.getvalue()) == (count < 3)
