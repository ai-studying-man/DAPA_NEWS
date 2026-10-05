"""Rules for excluding disallowed publishers and non-news content."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final
from urllib.parse import unquote, urlsplit

from dapa_morning_brief.opinion_evidence import author_opinion_reason

if TYPE_CHECKING:
    from dapa_morning_brief.models import Article

_BLOCKED_PUBLISHER_HOSTS: Final = frozenset({"digitalchosun.dizzo.com"})
_BLOCKED_PUBLISHER_LABELS: Final = (
    "조선일보",
    "조선비즈",
    "디지틀조선일보",
    "디지털조선일보",
)
_PERSONAL_PUBLISHING_HOSTS: Final = frozenset(
    {
        "blog.naver.com",
        "m.blog.naver.com",
        "brunch.co.kr",
        "medium.com",
        "blog.daum.net",
    }
)
_SERIAL_EPISODE_TITLE: Final = re.compile(
    r"^\s*(?:\[\s*\d+\s*화\s*\]|제\s*\d+\s*화\b)",
)
# Labels identify the article's genre; mentions within a reported headline do not.
_NON_NEWS_LABEL: Final = re.compile(
    r"""
    [\[【〈<](?:[^\]】〉>]{0,24}\s)?
    (?:사설|칼럼|컬럼|기고|독자\s*(?:기고|투고)|시론|논단|시평|오피니언|노트북\s*을\s*열며|기자의\s*눈|기자수첩|만평|웹툰|만화|
    연재\s*소설|웹\s*소설|소설|픽션|opinion|editorial|column|webtoon|comic|fiction)
    (?:\s*[^\]】〉>]{0,24})?[\]】〉>]
    """,
    re.VERBOSE | re.IGNORECASE,
)
_NON_NEWS_PREFIX: Final = re.compile(
    r"""
    ^\s*(?:사설|칼럼|컬럼|기고|시론|논단|시평|오피니언|노트북\s*을\s*열며|기자의\s*눈|기자수첩|
    만평|웹툰|연재\s*소설|웹\s*소설|
    opinion|editorial|column|webtoon|fiction)\s*[:\uFF1A]
    """,
    re.VERBOSE | re.IGNORECASE,
)
_NON_NEWS_PATH: Final = re.compile(
    r"""
    /(?:opinion|opinions|editorial|editorials|column|columns|webtoon|webtoons|
    comic|comics|cartoon|cartoons|fiction|novel|novels)(?:/|\.|$)
    """,
    re.VERBOSE | re.IGNORECASE,
)
_SERIES_DESCRIPTION: Final = re.compile(
    r"^\s*(?:웹툰|만화|웹\s*소설|연재\s*소설)\s*(?:연재|제\s*\d+\s*화|[:\uFF1A])",
)
# Only an item's own declaration is evidence. Generic fictional-work references
# occur in genuine reporting, so never scan the body for isolated genre keywords.
_FICTION_DISCLAIMER: Final = re.compile(
    r"""
    (?:이\s*(?:글|이야기|작품)|본\s*(?:작품|웹툰|만화|소설)|
    가상의?\s*인물과\s*허구의\s*사건을\s*다룬\s*이야기)
    [^.!?\n]{0,160}(?:허구|가상의?\s*(?:인물|상황)|실존하지\s*않는\s*인물)|
    ^\s*허구의\s*인물과\s*가상의?\s*상황을\s*다루는\s*소설\s*연재물|
    ^\s*가상의?\s*인물과\s*허구의\s*사건을\s*다룬\s*이야기(?:입니다|이다)
    """,
    re.VERBOSE,
)
_OPINION_DISCLAIMER: Final = re.compile(
    r"""
    (?:이\s*글|본\s*(?:글|기고|칼럼))[^.!?\n]{0,100}
    (?:필자|작성자)의\s*개인(?:적(?:인)?)?\s*(?:견해|의견)|
    (?:필자|작성자)의\s*(?:견해|의견)[^.!?\n]{0,60}
    (?:본지|편집|언론사)[^.!?\n]{0,60}다를\s*수
    """,
    re.VERBOSE,
)


def is_excluded_publisher(*, source: str, url: str) -> bool:
    """Identify Chosun publisher hosts and source labels."""
    hostname = (urlsplit(url).hostname or "").casefold().rstrip(".")
    if hostname == "chosun.com" or hostname.endswith(".chosun.com"):
        return True
    if hostname in _BLOCKED_PUBLISHER_HOSTS:
        return True
    source_label = source.casefold()
    return any(label.casefold() in source_label for label in _BLOCKED_PUBLISHER_LABELS)


def fiction_exclusion_reason(article: Article, body: str) -> str | None:
    """Exclude an item's own non-news genre without rejecting reports about it."""
    if is_excluded_publisher(source=article.source, url=article.url):
        return "excluded_publisher"
    hostname = (urlsplit(article.url).hostname or "").casefold().rstrip(".")
    metadata_rules = (
        (
            "non_news_publisher",
            hostname in _PERSONAL_PUBLISHING_HOSTS
            or hostname == "tistory.com"
            or hostname.endswith((".tistory.com", ".brunch.co.kr", ".medium.com")),
        ),
        ("non_news_header", bool(_SERIES_DESCRIPTION.search(article.description))),
        ("serialized_episode", bool(_SERIAL_EPISODE_TITLE.search(article.title))),
        (
            "non_news_label",
            bool(
                _NON_NEWS_LABEL.search(article.title)
                or _NON_NEWS_PREFIX.search(article.title)
            ),
        ),
        (
            "non_news_section",
            bool(_NON_NEWS_PATH.search(unquote(urlsplit(article.url).path))),
        ),
    )
    for reason, matches in metadata_rules:
        if matches:
            return reason
    for text in (article.description, body):
        if _FICTION_DISCLAIMER.search(text):
            return "fictional_content"
        if _OPINION_DISCLAIMER.search(text):
            return "personal_opinion"
    if body and (_NON_NEWS_LABEL.match(body.lstrip()) or _NON_NEWS_PREFIX.match(body)):
        return "non_news_header"
    return author_opinion_reason(f"{article.description} {body}")
