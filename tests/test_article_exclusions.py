from __future__ import annotations

import logging
from datetime import UTC, datetime

import pytest

from dapa_morning_brief.article_exclusions import (
    fiction_exclusion_reason,
    is_excluded_publisher,
)
from dapa_morning_brief.briefing import build_briefing
from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.models import Article, Section
from dapa_morning_brief.rss_parser import parse_rss_items


@pytest.mark.parametrize(
    ("url", "source"),
    [
        ("https://www.chosun.com/premium/story", "조선일보"),
        ("https://biz.chosun.com/industry/story", "조선비즈"),
        ("https://digitalchosun.dizzo.com/news/story", "디지틀조선일보"),
        ("https://news.google.com/rss/articles/id", "조선일보"),
    ],
)
def test_chosun_publisher_family_is_excluded(url: str, source: str) -> None:
    assert is_excluded_publisher(source=source, url=url)


def test_rss_parser_drops_chosun_article_before_accepting_candidate() -> None:
    xml = """<rss><channel><item>
      <title>국방부 차관 관련 보도</title>
      <link>https://www.chosun.com/premium/story</link>
      <pubDate>Wed, 30 Sep 2026 00:00:00 GMT</pubDate>
      <source>조선일보</source>
    </item></channel></rss>"""
    articles = parse_rss_items(
        xml,
        source_name="Google News",
        default_section=None,
        days=1,
        now=datetime(2026, 9, 30, tzinfo=UTC),
    )

    assert articles == []


def test_serialized_fiction_with_ministry_keywords_is_rejected_by_body() -> None:
    article = Article(
        title="[59화] 국방부 차관이 매국노가 된 이유",
        url="https://publisher.example/series/59",
        published_at=datetime(2026, 9, 30, tzinfo=UTC),
        source="테스트뉴스",
        section=Section.GOVERNMENT,
    )

    reason = fiction_exclusion_reason(
        article,
        (
            "허구의 인물과 가상의 상황을 다루는 소설 연재물입니다. "
            "등장인물은 실제 인물이 아닙니다."
        ),
    )

    assert reason is not None


def test_fictional_characters_are_rejected_even_without_episode_title() -> None:
    article = Article(
        title="국방부 차관을 둘러싼 의혹",
        url="https://publisher.example/story",
        published_at=datetime(2026, 9, 30, tzinfo=UTC),
        source="테스트뉴스",
        section=Section.GOVERNMENT,
    )

    assert (
        fiction_exclusion_reason(
            article,
            "이 글은 실존하지 않는 인물을 주인공으로 삼은 허구의 이야기입니다.",
        )
        is not None
    )


def test_real_training_scenario_is_not_mistaken_for_fiction() -> None:
    article = Article(
        title="국방부, 연합훈련 대응태세 점검",
        url="https://publisher.example/training",
        published_at=datetime(2026, 9, 30, tzinfo=UTC),
        source="테스트뉴스",
        section=Section.GOVERNMENT,
        description="가상 시나리오 기반 연합훈련 결과를 발표했다.",
    )

    assert (
        fiction_exclusion_reason(
            article,
            "국방부는 가상 시나리오를 활용한 연합훈련을 실시하고 대응태세를 점검했다.",
        )
        is None
    )


def test_unavailable_body_does_not_allow_numbered_fiction_episode() -> None:
    article = Article(
        title="[59화] 국방부 차관이 매국노가 된 이유",
        url="https://publisher.example/series/59",
        published_at=datetime(2026, 9, 30, tzinfo=UTC),
        source="테스트뉴스",
        section=Section.GOVERNMENT,
    )

    assert fiction_exclusion_reason(article, "") == "serialized_episode"


def test_fiction_candidate_is_removed_before_section_quota_is_filled(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fictional = Article(
        title="국방부 차관의 선택",
        url="https://publisher.example/fiction",
        published_at=datetime(2026, 9, 30, 8, tzinfo=UTC),
        source="테스트뉴스",
        section=Section.GOVERNMENT,
    )
    factual = Article(
        title="국방부, 장병 복지정책 발표",
        url="https://publisher.example/factual",
        published_at=datetime(2026, 9, 30, 7, tzinfo=UTC),
        source="테스트뉴스",
        section=Section.GOVERNMENT,
    )
    bodies = (
        ArticleBody(
            article_url=fictional.url,
            title=fictional.title,
            source=fictional.source,
            body="가상의 인물과 허구의 사건을 다룬 이야기입니다.",
        ),
        ArticleBody(
            article_url=factual.url,
            title=factual.title,
            source=factual.source,
            body="국방부는 장병 복지정책을 발표하고 다음 달부터 시행한다.",
        ),
    )

    with caplog.at_level(logging.WARNING, logger="dapa_morning_brief.briefing"):
        briefing = build_briefing(
            (fictional, factual),
            max_per_section=1,
            article_bodies=bodies,
        )

    assert briefing.sections[Section.GOVERNMENT] == (factual,)
    assert "news_candidate_excluded reason=fictional_content" in caplog.text
