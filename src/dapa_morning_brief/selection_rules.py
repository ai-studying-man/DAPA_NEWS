"""Editorial coverage signals used within bounded newsletter selection."""

import re
from typing import Final
from urllib.parse import urlsplit

from dapa_morning_brief.headline_rules import has_acquisition_accountability_topic
from dapa_morning_brief.models import Article

PHOTO_LABEL: Final[re.Pattern[str]] = re.compile(r"[\[【(](?:사진|포토|화보)[\]】)]")
MIN_SUBSTANTIVE_BODY: Final = 200


def is_acquisition_accountability(article: Article) -> bool:
    """Reserve agency-led scrutiny, not incidental agency background mentions."""
    return has_acquisition_accountability_topic(
        article.title, article.description
    ) and not is_photo_article(article)


def is_photo_article(article: Article) -> bool:
    """Recognize explicit photo labels and gallery routes across publishers."""
    path = urlsplit(article.url).path.casefold()
    return PHOTO_LABEL.search(article.title) is not None or any(
        part in path for part in ("/photos/", "/gallery/")
    )
