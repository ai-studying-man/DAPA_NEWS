"""Identify article-specific opinion genres and author-led proposals."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Final, final

from typing_extensions import override

MIN_EDITORIAL_SIGNALS: Final = 2
_GENRE: Final = re.compile(
    r"^(?:오피니언|사설|칼럼|논평|기고|시론|논단|opinion|editorial|column|commentary)$",
    re.IGNORECASE,
)
_AUTHOR_PROPOSAL: Final = re.compile(
    r"(?:필자|논객|칼럼니스트)[^.!?]{0,80}(?:논평|제안|주장)|(?:논평|기고|칼럼)을?\s*통해[^.!?]{0,120}(?:제안|주장)"
)
_ATTRIBUTED: Final = re.compile(
    r"(?:밝혔|말했|설명했|주장했|촉구했|요구했|발표했|강조했|지적했|전했다|덧붙였|전문가|의원|대변인)"
)
_PRESCRIPTION: Final = re.compile(
    r"(?:해야\s*(?:한다|할\s*것)|바꿔야\s*한다|물어야\s*한다|대야\s*한다|해서는\s*안\s*된다)"
)
_THESIS: Final = re.compile(
    r"그러나\s*문제는|국민이\s*묻는\s*핵심|국민\s*입장에서는|학생을\s*탓하기\s*전에|자주국방은[^.!?]{0,80}아니다"
)


@final
class _ArticleGenreParser(HTMLParser):
    """Accumulate metadata and article-header labels, never site menu labels."""

    def __init__(self) -> None:
        super().__init__()
        self.labels: list[str] = []
        self._header = False

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "meta" and (
            attributes.get("property") or attributes.get("name") or ""
        ).casefold() in {"article:section", "article:section1", "section", "genre"}:
            self.labels.append(attributes.get("content") or "")
        if (
            tag == "header"
            and "article-view-header" in (attributes.get("class") or "").split()
        ):
            self._header = True

    @override
    def handle_endtag(self, tag: str) -> None:
        if tag == "header":
            self._header = False

    @override
    def handle_data(self, data: str) -> None:
        if self._header:
            self.labels.append(data.strip())


def publisher_opinion_reason(html: str) -> str | None:
    """Read only the fetched article's genre evidence."""
    parser = _ArticleGenreParser()
    parser.feed(html)
    return (
        "publisher_opinion"
        if any(_GENRE.fullmatch(label.strip()) for label in parser.labels)
        else None
    )


def author_opinion_reason(text: str) -> str | None:
    """Reject author proposals and multiple unquoted editorial prescriptions."""
    lead = text[:2200]
    if _AUTHOR_PROPOSAL.search(lead):
        return "author_proposal"
    unquoted = re.sub(r'[“"「][^”"」]*[”"」]', "", lead)
    sentences = [s for s in re.split(r"[.!?\n]", unquoted) if not _ATTRIBUTED.search(s)]
    prescriptions = sum(bool(_PRESCRIPTION.search(s)) for s in sentences)
    theses = sum(bool(_THESIS.search(s)) for s in sentences)
    return (
        "editorial_argument"
        if prescriptions >= MIN_EDITORIAL_SIGNALS or theses >= MIN_EDITORIAL_SIGNALS
        else None
    )
