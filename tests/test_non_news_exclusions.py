from __future__ import annotations

from datetime import UTC, datetime

import pytest

from dapa_morning_brief.article_exclusions import fiction_exclusion_reason
from dapa_morning_brief.briefing import build_briefing, build_candidate_pool
from dapa_morning_brief.models import Article, Section
from dapa_morning_brief.rss_parser import parse_rss_items


def _article(title: str, path: str = "/news/report") -> Article:
    return Article(
        title=title,
        url=f"https://publisher.example{path}",
        published_at=datetime(2026, 10, 4, tzinfo=UTC),
        source="테스트뉴스",
        section=Section.POLICY,
    )


@pytest.mark.parametrize(
    "title",
    [
        "[사설] 국방 예산 재검토해야",
        "[홍길동 칼럼] 방산 정책의 미래",
        "[기고] 국방 정책 방향",
        "국방 예산 재검토해야 [사설]",
        "[웹툰] 국방부 장관의 비밀",
        "[만평] 국방 예산",
        "[연재소설] 방산의 미래",
    ],
)
def test_labeled_non_news_is_removed_from_candidate_and_final(title: str) -> None:
    # Given: a relevant but explicitly non-news item.
    article = _article(title)
    # When: the shared rule and both selection surfaces inspect it.
    reason = fiction_exclusion_reason(article, "")
    pool = build_candidate_pool((article,), max_per_section=5)
    final = build_briefing((article,), max_per_section=5)
    # Then: it never occupies a news slot.
    assert reason is not None
    assert pool.sections[Section.POLICY] == ()
    assert final.sections[Section.POLICY] == ()


@pytest.mark.parametrize("path", ["/opinion/column/42", "/webtoon/42", "/fiction/42"])
def test_non_news_paths_are_rejected_without_body(path: str) -> None:
    # Given: a misleading news-like title in a non-news section.
    article = _article("국방부 정책 변화", path)
    # When: metadata is inspected.
    reason = fiction_exclusion_reason(article, "")
    # Then: section metadata excludes it.
    assert reason is not None


@pytest.mark.parametrize(
    "body",
    [
        "이 글은 필자의 개인적인 견해이며 본지의 편집 방향과 다를 수 있습니다.",
        "본 웹툰의 등장인물과 사건은 모두 허구입니다.",
    ],
)
def test_first_party_disclaimer_rejects_non_news(body: str) -> None:
    # Given: metadata resembles reporting but the author declares otherwise.
    article = _article("국방부 정책 변화")
    # When: the body is inspected.
    reason = fiction_exclusion_reason(article, body)
    # Then: the declaration prevents selection.
    assert reason is not None


@pytest.mark.parametrize(
    ("title", "body"),
    [
        (
            "국방부, 웹툰 활용 장병 교육 시행",
            "국방부는 웹툰과 소설 속 등장인물을 활용한 교육을 시행했다.",
        ),
        (
            "방산 기업, 허구의 사건 다룬 웹툰 저작권 계약",
            "작품은 허구의 인물을 다루는 웹소설이다. 기업은 계약을 발표했다.",
        ),
        (
            "국방 예산 관련 사설에 정부 해명",
            "국방부는 신문 사설의 의견에 대해 공식 입장을 밝혔다.",
        ),
        (
            "국방부, 군 장병 의견 수렴",
            "국방부는 장병 개인의 견해를 정책에 반영하기 위해 의견을 수렴했다.",
        ),
    ],
)
def test_reporting_about_non_news_remains_eligible(title: str, body: str) -> None:
    # Given: actual reporting mentions creative works or opinions.
    article = _article(title)
    # When: the exclusion rule examines the report.
    reason = fiction_exclusion_reason(article, body)
    # Then: mentioning those subjects is not a non-news declaration.
    assert reason is None


def test_rss_discards_labeled_column_before_candidate_collection() -> None:
    # Given: an RSS item explicitly labeled as a column.
    xml = """<rss><channel><item><title>[칼럼] 방위사업청 정책 방향</title>
    <link>https://publisher.example/report</link>
    <pubDate>Sun, 04 Oct 2026 00:00:00 GMT</pubDate>
    </item></channel></rss>"""
    # When: RSS enters the collection pipeline.
    articles = parse_rss_items(
        xml,
        source_name="테스트뉴스",
        default_section=None,
        days=1,
        now=datetime(2026, 10, 4, tzinfo=UTC),
    )
    # Then: it is not accepted as a news candidate.
    assert articles == []


def test_candidate_pool_rechecks_blocked_publisher_on_direct_input() -> None:
    # Given: a direct collector bypasses the RSS parser.
    article = Article(
        title="방위사업청 정책 발표",
        url="https://biz.chosun.com/report",
        published_at=datetime(2026, 10, 4, tzinfo=UTC),
        source="조선비즈",
        section=Section.POLICY,
    )
    # When: the candidate pool is built.
    pool = build_candidate_pool((article,), max_per_section=5)
    # Then: publisher exclusions still apply.
    assert pool.sections[Section.POLICY] == ()


@pytest.mark.parametrize(
    "label", ["노트북을 열며", "기자의 눈", "기자수첩", "시평", "오피니언"]
)
def test_known_opinion_series_labels_rejected_on_opaque_news_url(label: str) -> None:
    # Given: an opinion series uses the publisher's ordinary article route.
    article = _article(f"[{label}] KAI 지배구조와 방산 정책", "/article/42")
    # When: collection and final selection inspect the metadata.
    pool = build_candidate_pool((article,), max_per_section=5)
    final = build_briefing((article,), max_per_section=5)
    # Then: an opaque route cannot bypass the genre label.
    assert pool.sections[Section.POLICY] == ()
    assert final.sections[Section.POLICY] == ()


@pytest.mark.parametrize(
    "host",
    [
        "blog.naver.com",
        "m.blog.naver.com",
        "brunch.co.kr",
        "medium.com",
        "writer.tistory.com",
        "blog.daum.net",
    ],
)
def test_personal_blog_platforms_rejected_at_all_collection_boundaries(
    host: str,
) -> None:
    # Given: a personal publishing post has a news-like title.
    article = Article(
        title="방위사업청 국방 예산 정책 발표",
        url=f"https://{host}/post/42",
        published_at=datetime(2026, 10, 4, tzinfo=UTC),
        source="개인 게시물",
        section=Section.POLICY,
    )
    xml = f"""<rss><channel><item><title>{article.title}</title>
    <link>{article.url}</link>
    <pubDate>Sun, 04 Oct 2026 00:00:00 GMT</pubDate></item></channel></rss>"""
    # When: each externally reachable collection surface inspects it.
    reason = fiction_exclusion_reason(article, "")
    pool = build_candidate_pool((article,), max_per_section=5)
    final = build_briefing((article,), max_per_section=5)
    rss = parse_rss_items(
        xml,
        source_name="개인 게시물",
        default_section=None,
        days=1,
        now=datetime(2026, 10, 4, tzinfo=UTC),
    )
    # Then: personal publication never fills a news quota.
    assert reason == "non_news_publisher"
    assert pool.sections[Section.POLICY] == ()
    assert final.sections[Section.POLICY] == ()
    assert rss == []


def test_series_episode_rejected_when_description_declares_webtoon() -> None:
    # Given: a series title hides its genre but the metadata declares it.
    article = Article(
        title="무기 이야기 12화",
        url="https://publisher.example/article/42",
        description="웹툰 연재: 무기 이야기를 매주 소개합니다.",
        published_at=datetime(2026, 10, 4, tzinfo=UTC),
        source="테스트뉴스",
        section=Section.POLICY,
    )
    # When: the candidate rule sees the item's own genre declaration.
    reason = fiction_exclusion_reason(article, "")
    # Then: it cannot be collected as reporting.
    assert reason is not None


@pytest.mark.parametrize(
    "title",
    [
        "국방부, 웹툰 무기 이야기 12화 공개",
        "[현장] 국방부 기자수첩 논란 관련 브리핑",
        "방산 기업, 네이버 블로그로 채용 정보 공개",
    ],
)
def test_reporting_with_genre_mentions_or_generic_tags_is_preserved(title: str) -> None:
    # Given: a genuine report mentions a creative work or publication.
    article = _article(title)
    # When: the genre rules inspect the headline.
    reason = fiction_exclusion_reason(article, "")
    # Then: only its own genre is grounds for rejection.
    assert reason is None
