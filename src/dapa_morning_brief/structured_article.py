"""Recover publisher-declared article text when visible extraction is empty."""

from __future__ import annotations

from html.parser import HTMLParser
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError
from typing_extensions import override

_ARTICLE_TYPES: Final = frozenset({"Article", "NewsArticle", "ImageGallery"})
_MIN_CAPTION_WORDS: Final = 3


class _Image(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    caption: str = ""


class _Node(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    schema_type: str | tuple[str, ...] = Field(default="", alias="@type")
    article_body: str = Field(default="", alias="articleBody")
    image: str | _Image | tuple[str | _Image, ...] = ()
    graph: tuple[_Node, ...] = Field(default=(), alias="@graph")


_SCHEMA: Final[TypeAdapter[_Node | tuple[_Node, ...]]] = TypeAdapter(
    _Node | tuple[_Node, ...],
)


class _JsonScripts(HTMLParser):
    """Accumulate JSON-LD script text without reading navigation or image alt text."""

    def __init__(self) -> None:
        super().__init__()
        self.scripts: list[str] = []
        self.parts: list[str] = []
        self.collecting: bool = False

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script":
            self.collecting = dict(attrs).get("type") == "application/ld+json"
            self.parts = []

    @override
    def handle_data(self, data: str) -> None:
        if self.collecting:
            self.parts.append(data)

    @override
    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self.collecting:
            self.scripts.append("".join(self.parts))
            self.collecting = False


def extract_structured_article(html_text: str) -> str | None:
    """Read article bodies or their attached photo captions, never unrelated images."""
    parser = _JsonScripts()
    parser.feed(html_text)
    for script in parser.scripts:
        try:
            parsed = _SCHEMA.validate_json(script)
        except ValidationError:
            continue
        match parsed:
            case _Node():
                nodes = [parsed]
            case tuple():
                nodes = list(parsed)
        for node in nodes:
            nodes.extend(node.graph)
            text = _article_text(node)
            if text:
                return text
    return None


def _article_text(node: _Node) -> str | None:
    match node.schema_type:
        case str():
            kinds = (node.schema_type,)
        case tuple():
            kinds = node.schema_type
    if not _ARTICLE_TYPES.intersection(kinds):
        return None
    if node.article_body.strip():
        return " ".join(node.article_body.split())
    match node.image:
        case str():
            images = ()
        case _Image():
            images = (node.image,)
        case tuple():
            images = node.image
    captions = dict.fromkeys(
        " ".join(image.caption.split())
        for image in images
        if isinstance(image, _Image)
        and len(image.caption.split()) >= _MIN_CAPTION_WORDS
    )
    return " ".join(captions) or None
