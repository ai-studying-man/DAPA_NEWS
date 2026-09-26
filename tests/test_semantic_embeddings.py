"""Exercise real native ONNX exceptions without downloading a model."""

from datetime import UTC, datetime
from typing import Never

import pytest

from dapa_morning_brief import semantic_embeddings
from dapa_morning_brief.models import Article, Section
from dapa_morning_brief.semantic_deduplication import create_semantic_index

pytest.importorskip("onnxruntime")
from onnxruntime.capi.onnxruntime_pybind11_state import (
    DeviceReset,
    EngineError,
    EPFail,
    Fail,
    InvalidArgument,
    InvalidGraph,
    InvalidProtobuf,
    ModelLoadCanceled,
    ModelLoaded,
    ModelRequiresCompilation,
    NoModel,
    NoSuchFile,
    NotFound,
    RuntimeException,
)
from onnxruntime.capi.onnxruntime_pybind11_state import (
    NotImplemented as OnnxNotImplemented,
)


def articles() -> tuple[Article, Article]:
    return (
        Article("first", "a", datetime(2026, 1, 1, tzinfo=UTC), "news", Section.POLICY),
        Article(
            "second", "b", datetime(2026, 1, 1, tzinfo=UTC), "news", Section.POLICY
        ),
    )


@pytest.mark.parametrize(
    "error_type",
    [
        DeviceReset,
        EngineError,
        EPFail,
        Fail,
        InvalidArgument,
        InvalidGraph,
        InvalidProtobuf,
        ModelLoadCanceled,
        ModelLoaded,
        ModelRequiresCompilation,
        NoModel,
        NoSuchFile,
        NotFound,
        OnnxNotImplemented,
        RuntimeException,
    ],
)
def test_native_model_error_retains_lexical_fallback(
    error_type: type[Exception],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Given a real ONNX native failure during lazy model loading.
    def failed_model() -> Never:
        message = "native model failure"
        raise error_type(message)

    monkeypatch.setattr(semantic_embeddings, "_model", failed_model)
    # When the model boundary handles that failure.
    index = create_semantic_index(articles(), ())
    # Then semantic scoring degrades visibly, leaving lexical matching available.
    assert index.scored_articles == 0
    assert "WARNING" in caplog.text
    assert "lexical matching retained" in caplog.text


@pytest.mark.parametrize("error_type", [TypeError, AttributeError, KeyError])
def test_programming_error_is_not_hidden(
    error_type: type[Exception], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given a programming error rather than a native model failure.
    def broken_model() -> Never:
        message = "programming error"
        raise error_type(message)

    monkeypatch.setattr(semantic_embeddings, "_model", broken_model)
    # When indexing, then the programmer sees the original error.
    with pytest.raises(error_type):
        _ = create_semantic_index(articles(), ())
