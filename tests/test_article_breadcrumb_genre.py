from dapa_morning_brief.opinion_evidence import publisher_opinion_reason


def test_article_breadcrumb_identifies_contributed_opinion() -> None:
    # Given: article-local genre markup used by the publisher, not site navigation.
    html = (
        '<div class="location"><span>오피니언</span>'
        '<span class="last">기고</span></div>'
    )
    # When
    reason = publisher_opinion_reason(html)
    # Then
    assert reason == "publisher_opinion"


def test_news_article_is_retained_when_global_menu_contains_opinion() -> None:
    # Given
    html = (
        '<nav><a>오피니언</a><a>기고</a></nav>'
        '<div class="location"><span>국방뉴스</span><span>국방정책</span></div>'
    )
    # When
    reason = publisher_opinion_reason(html)
    # Then
    assert reason is None
