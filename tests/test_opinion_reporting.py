from datetime import UTC, datetime
from io import StringIO
from unittest.mock import patch

import httpx
import pytest

from dapa_morning_brief.article_content import fetch_article_bodies
from dapa_morning_brief.article_exclusions import fiction_exclusion_reason
from dapa_morning_brief.briefing import build_briefing
from dapa_morning_brief.cli import main
from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.models import Article, Briefing, Section
from tests.coverage_samples import coverage_articles


def article() -> Article:
    return Article(
        title="국방부 방위사업 관련 소식",
        url="https://news.test/1",
        published_at=datetime(2026, 10, 5, tzinfo=UTC),
        source="언론사",
        section=Section.POLICY,
    )


@pytest.mark.parametrize(
    "body",
    [
        """폴란드 전문매체는 필자의 논평을 통해 하이마스를 매각하고 천무를
추가 도입하는 방안을 제안했다. 정부의 매각 발표나 군의 공식
방침은 아니다.""",
        """그러나 문제는 탐지할 수 있다는 것과 실제로 요격할 수 있다는
것은 전혀 다른 문제라는 점이다. 국민이 묻는 핵심은 따로
있다. 정부는 대응 원칙도 분명히 해야 한다.""",
        (
            """학생을 탓하기 전에 제도에 매스를 가져다 대야 한다. 먼저
책임을 물어야 한다. 이제 관계당국은 근본적으로 바꿔야 한다."""
        ),
    ],
)
def test_author_proposals_and_editorial_theses_are_excluded(body: str) -> None:
    assert fiction_exclusion_reason(article(), body) is not None
    inspected = ArticleBody(article().url, article().title, article().source, body)
    selected = build_briefing(
        [article()], max_per_section=5, article_bodies=[inspected]
    )
    assert not selected.sections[Section.POLICY]


@pytest.mark.parametrize(
    "body",
    [
        (
            """국방부는 탐지·요격이 가능하다고 발표했다.
전문가 김씨는 추가 검증이 필요하다는 의견을 밝혔다."""
        ),
        (
            """폴란드 정부는 천무 추가 도입 계약을 체결했다고 발표했다.
납품은 2030년부터 시작할 예정이다."""
        ),
        '국회는 정부에 개선을 촉구했다. 의원은 "지원 제도를 바꿔야 한다"고 말했다.',
    ],
)
def test_fact_reporting_and_attributed_quotes_are_preserved(body: str) -> None:
    assert fiction_exclusion_reason(article(), body) is None


@pytest.mark.parametrize(
    ("markup", "excluded"),
    [
        (
            ('<meta property="article:section" content="오피니언">'),
            True,
        ),
        (
            ('<header class="article-view-header"><a>칼럼</a></header>'),
            True,
        ),
        (
            (
                """<nav><a>오피니언</a></nav><footer><a>칼럼</a></footer><meta
property="article:section"
content="정치">"""
            ),
            False,
        ),
    ],
)
def test_publisher_article_genre_excludes_without_using_global_menus(
    markup: str, excluded: bool
) -> None:
    html = markup + (
        """<article><p>국방부는 신규 방위사업 계획을 발표했다.
조달 일정과 예산 집행 계획을
공개했다.</p></article>"""
    )
    response = httpx.Response(
        200, text=html, request=httpx.Request("GET", article().url)
    )
    with patch("httpx.Client.get", return_value=response):
        bodies = fetch_article_bodies(Briefing(sections={Section.POLICY: (article(),)}))
    result = build_briefing([article()], max_per_section=5, article_bodies=bodies)
    assert bool(result.sections[Section.POLICY]) is not excluded


def test_opinion_body_rejection_triggers_backfill_for_valid_news() -> None:

    samples = coverage_articles(3)
    policies = [a for a in samples if a.section == Section.POLICY]
    daily = [a for a in samples if a.section != Section.POLICY] + policies[:1]
    rejected = ArticleBody(
        policies[0].url,
        policies[0].title,
        policies[0].source,
        "필자의 논평을 통해 무기 매각을 제안했다.",
    )
    extra = coverage_articles(5)
    with (
        patch(
            "dapa_morning_brief.cli.collect_articles", side_effect=[daily, extra]
        ) as collect,
        patch(
            "dapa_morning_brief.cli.fetch_article_bodies", side_effect=[(rejected,), ()]
        ),
        patch(
            ("dapa_morning_brief.cli.collect_weather_forecasts"),
            return_value=(),
        ),
        patch("sys.stdout", StringIO()) as output,
        patch("dapa_morning_brief.cli.send_telegram_messages") as send,
    ):
        assert main(["--dry-run"]) == 0
    assert [c.kwargs["days"] for c in collect.call_args_list] == [1, 2]
    assert policies[0].url not in output.getvalue()
    assert (
        sum(a.url in output.getvalue() for a in extra if a.section == Section.POLICY)
        >= 3
    )
    send.assert_not_called()
