"""Semantic duplicate comparison regression tests (no model downloads)."""

import math
from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from dapa_morning_brief import semantic_deduplication as semantic
from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.models import Article, Section


def article(title: str, url: str, description: str = "") -> Article:
    return Article(
        title,
        url,
        datetime(2026, 1, 1, tzinfo=UTC),
        "news",
        Section.EXPORT_BUSINESS,
        description,
    )


def test_paraphrases_match_when_content_and_title_agree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given two differently phrased reports with corroborating content.
    articles = (
        article("K9 수출 계약 체결", "a", "내용 " * 50),
        article("K9 공급 최종 서명", "b", "보도 " * 50),
    )
    monkeypatch.setattr(
        semantic,
        "_encode",
        encoder(((3.0, 0.0), (3.0, 0.0), (0.99, 0.1), (0.99, 0.1))),
    )
    # When embeddings are indexed.
    index = semantic.create_semantic_index(articles, ())
    # Then normalized semantic comparison detects the duplicate.
    assert index.are_same(*articles)
    assert index.scored_articles == 2
    assert index.content_articles == 2


@pytest.mark.parametrize(
    "titles",
    [
        ("K9 폴란드 수출 계약 체결", "K9 루마니아 수출 계약 체결"),
        ("K9 수출 계약 체결", "K9 수출 계약 취소"),
    ],
)
def test_contradictory_events_survive_even_with_identical_vectors(
    titles: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given embeddings that cannot distinguish crucial title facts.
    articles = (article(titles[0], "a"), article(titles[1], "b"))
    monkeypatch.setattr(semantic, "_encode", encoder(((1.0, 0.0),) * 4))
    # When indexed.
    index = semantic.create_semantic_index(articles, ())
    # Then explicit contradictory facts prevent a merge.
    assert not index.are_same(*articles)


@pytest.mark.parametrize("threshold", ["nan", "inf", "-0.1", "1.1", "oops"])
def test_invalid_threshold_raises(
    monkeypatch: pytest.MonkeyPatch, threshold: str
) -> None:
    # Given an invalid operator setting.
    monkeypatch.setenv("DAPA_SEMANTIC_THRESHOLD", threshold)
    # When parsed, then it raises clearly even for an empty input.
    with pytest.raises(ValueError, match="DAPA_SEMANTIC_THRESHOLD"):
        _ = semantic.create_semantic_index((), ())


def test_model_failure_returns_empty_index(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # Given an unavailable embedding model.
    def unavailable(_texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        message = "unavailable"
        raise OSError(message)

    monkeypatch.setattr(semantic, "_encode", unavailable)
    articles = (article("title", "a"), article("other", "b"))
    # When indexed.
    index = semantic.create_semantic_index(articles, ())
    # Then the caller can retain lexical matching and sees the degradation.
    assert not index.are_same(*articles)
    assert index.scored_articles == 0
    assert "WARNING" in caplog.text


def test_title_only_requires_stricter_similarity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given title cosine similarity .93, below the metadata-only threshold.
    articles = (article("first", "a"), article("second", "b"))
    vector = (0.93, math.sqrt(1 - 0.93**2))
    monkeypatch.setattr(
        semantic, "_encode", encoder(((1.0, 0.0), (1.0, 0.0), vector, vector))
    )
    # When indexed.
    index = semantic.create_semantic_index(articles, ())
    # Then broad topic similarity is not enough.
    assert not index.are_same(*articles)


def encoder(
    vectors: tuple[tuple[float, ...], ...],
) -> Callable[[tuple[str, ...]], tuple[tuple[float, ...], ...]]:
    def encode(_texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return vectors

    return encode


@pytest.mark.parametrize("body", ["", "본문 " * 50])
def test_opposite_contract_outcome_survives_with_body(
    body: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given opposite outcomes with artificially identical embeddings.
    articles = (article("K9 수출 계약 체결", "a"), article("K9 수출 계약 취소", "b"))
    bodies = tuple(
        ArticleBody(item.url, item.title, item.source, body) for item in articles
    )
    monkeypatch.setattr(semantic, "_encode", encoder(((1.0,),) * 4))
    # When indexed, then neither metadata nor full content overrides the contradiction.
    assert not semantic.create_semantic_index(articles, bodies).are_same(*articles)


@pytest.mark.parametrize(
    "titles",
    [
        ("K9 폴란드 수출 계약 체결", "K9 폴란드 공군 인도 계약 체결"),
        ("K9 인도네시아 수출 계약", "K9 인도네시아 공급 계약"),
    ],
)
def test_delivery_word_or_longer_country_does_not_invent_target(
    titles: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given consistent destination facts with the word India embedded elsewhere.
    articles = (article(titles[0], "a"), article(titles[1], "b"))
    monkeypatch.setattr(semantic, "_encode", encoder(((1.0,),) * 4))
    # When indexed, then these titles can match.
    assert semantic.create_semantic_index(articles, ()).are_same(*articles)


@pytest.mark.parametrize(
    "vectors",
    [
        ((0.0,),) * 4,
        ((float("nan"),),) * 4,
        ((1.0,), (1.0, 0.0), (1.0,), (1.0,)),
        ((1.0,),),
    ],
)
def test_invalid_model_output_degrades_safely(
    vectors: tuple[tuple[float, ...], ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given malformed model output.
    monkeypatch.setattr(semantic, "_encode", encoder(vectors))
    # When indexed, then lexical fallback remains available.
    assert (
        semantic.create_semantic_index(
            (article("a", "a"), article("b", "b")), ()
        ).scored_articles
        == 0
    )


def test_single_article_skips_model(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given a model that must not be called for a single report.
    def unexpected(_texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        pytest.fail("single article invoked model")

    monkeypatch.setattr(semantic, "_encode", unexpected)
    # When indexed, then no embeddings are needed.
    assert semantic.create_semantic_index((article("a", "a"),), ()).scored_articles == 0


@pytest.mark.parametrize(("threshold", "expected"), [("0.93", True), ("0.95", False)])
def test_configured_content_threshold_changes_decision(
    threshold: str, expected: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given the same title and .94 content similarity.
    articles = (article("a", "a", "내용 " * 50), article("b", "b", "본문 " * 50))
    vector = (0.94, math.sqrt(1 - 0.94**2))
    monkeypatch.setenv("DAPA_SEMANTIC_THRESHOLD", threshold)
    monkeypatch.setattr(
        semantic, "_encode", encoder(((1.0, 0.0), (1.0, 0.0), (1.0, 0.0), vector))
    )
    # When indexed, then the operator's threshold controls the outcome.
    assert semantic.create_semantic_index(articles, ()).are_same(*articles) is expected


def test_encoder_receives_body_then_description_with_bounded_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given a full body and a description-only article.
    articles = (article("first", "a", "ignored"), article("second", "b", "D" * 1200))
    bodies = (ArticleBody("a", "first", "news", "B" * 1200),)
    observed: list[tuple[str, ...]] = []

    def capture(texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        observed.append(texts)
        return ((1.0,),) * len(texts)

    monkeypatch.setattr(semantic, "_encode", capture)
    # When indexed.
    _ = semantic.create_semantic_index(articles, bodies)
    # Then E5 prefixes and the 1000-character content limit are explicit.
    assert observed == [
        (
            "query: first",
            "query: first " + "B" * 1000,
            "query: second",
            "query: second " + "D" * 1000,
        )
    ]


def test_different_explicit_weapons_survive_identical_embeddings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given templated export reports about distinct weapons.
    articles = (
        article("K9 폴란드 수출 계약", "a"),
        article("K2 폴란드 수출 계약", "b"),
    )
    monkeypatch.setattr(semantic, "_encode", encoder(((1.0,),) * 4))
    # When indexed, then different weapon identifiers preserve separate stories.
    assert not semantic.create_semantic_index(articles, ()).are_same(*articles)


@pytest.mark.parametrize(
    ("title", "expected"), [("K9 계약 보도", False), ("K9 계약 인터뷰", True)]
)
def test_interview_frame_requires_matching_frame(
    title: str, expected: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given identical semantics but a distinct interview frame.
    articles = (article("K9 계약 인터뷰", "a"), article(title, "b"))
    monkeypatch.setattr(semantic, "_encode", encoder(((1.0,),) * 4))
    # When indexed, then only equally framed reports can merge semantically.
    assert semantic.create_semantic_index(articles, ()).are_same(*articles) is expected


def test_shared_trip_content_requires_specific_title_overlap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given near-identical trip context but only .83 title similarity.
    articles = (
        article("투자 행사", "a", "내용 " * 50),
        article("가수 만남", "b", "본문 " * 50),
    )
    vector = (0.83, math.sqrt(1 - 0.83**2))
    monkeypatch.setattr(
        semantic,
        "_encode",
        encoder(((1.0, 0.0), (1.0, 0.0), vector, (0.94, math.sqrt(1 - 0.94**2)))),
    )
    # When indexed, then topic overlap alone is insufficient.
    assert not semantic.create_semantic_index(articles, ()).are_same(*articles)


@pytest.mark.parametrize(("threshold", "expected"), [("0.93", True), ("0.98", False)])
def test_strong_content_supports_paraphrased_title(
    threshold: str, expected: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given .97 content support and a .83 paraphrased title.
    articles = (
        article("투자 발표", "a", "내용 " * 50),
        article("투자 협약", "b", "본문 " * 50),
    )
    title = (0.83, math.sqrt(1 - 0.83**2))
    content = (0.97, math.sqrt(1 - 0.97**2))
    monkeypatch.setenv("DAPA_SEMANTIC_THRESHOLD", threshold)
    monkeypatch.setattr(
        semantic, "_encode", encoder(((1.0, 0.0), (1.0, 0.0), title, content))
    )
    # When indexed, then strong support respects stricter operator thresholds.
    assert semantic.create_semantic_index(articles, ()).are_same(*articles) is expected
