from __future__ import annotations

import pytest

from dapa_morning_brief.article_content import extract_main_text


@pytest.mark.parametrize("schema_type", ["NewsArticle", "Article", "ImageGallery"])
def test_short_article_image_caption_becomes_body(schema_type: str) -> None:
    # Given
    html = f"""<html><head><script type="application/ld+json">{{
      "@type": "{schema_type}", "image": [
        {{"@type": "ImageObject", "caption": "합참, DMZ 지뢰 추정 폭발 사고 브리핑"}},
        {{"@type": "ImageObject", "caption": "합참, DMZ 지뢰 추정 폭발 사고 브리핑"}}
      ]}}</script></head><body></body></html>"""
    # When
    body = extract_main_text(html)
    # Then
    assert body == "합참, DMZ 지뢰 추정 폭발 사고 브리핑"


def test_unrelated_image_schema_is_not_article_text() -> None:
    # Given
    html = """<html><head><script type="application/ld+json">{
      "@type": "ImageObject", "caption": "합참, DMZ 지뢰 추정 폭발 사고 브리핑"
    }</script></head><body><nav>
    <img alt="합참, DMZ 지뢰 추정 폭발 사고 브리핑"></nav></body></html>"""
    # When
    body = extract_main_text(html)
    # Then
    assert body is None


def test_article_body_is_preferred_to_structured_photo_caption() -> None:
    # Given
    html = """<html><head><script type="application/ld+json">{
      "@type": "NewsArticle", "image": {
        "@type": "ImageObject", "caption": "관련 사진 설명"
      }}</script></head><body><article>
      <p>방위사업청은 무전기 납품 사업의 문제점을 조사했다.</p>
      <p>시험평가 결과에 따라 계약 조건을 재검토하고 후속 조치를 결정한다.</p>
      </article></body></html>"""
    # When
    body = extract_main_text(html)
    # Then
    assert body is not None
    assert "후속 조치" in body
    assert "관련 사진 설명" not in body


def test_invalid_json_does_not_block_later_article_schema() -> None:
    # Given
    html = """<script type="application/ld+json">{invalid</script>
    <script type="application/ld+json">{"@graph": [
      {"@type": "NewsArticle",
       "articleBody": "방위사업청은 무전기 납품 사업의 문제점을 조사했다."}
    ]}</script>"""
    # When
    body = extract_main_text(html)
    # Then
    assert body == "방위사업청은 무전기 납품 사업의 문제점을 조사했다."
