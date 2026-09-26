"""Verify cached model bytes before any native model loading."""

from hashlib import sha256
from importlib import reload
from pathlib import Path

import pytest

from dapa_morning_brief import semantic_embeddings


@pytest.mark.parametrize("tampered", [False, True])
def test_cached_model_is_verified_before_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, tampered: bool
) -> None:
    # Given a cached snapshot returned by the external Hub boundary.
    import huggingface_hub  # noqa: PLC0415

    payload = b"known model bytes"
    _ = (tmp_path / "model.onnx").write_bytes(b"corrupt" if tampered else payload)
    monkeypatch.setattr(
        semantic_embeddings,
        "_MODEL_FILES",
        (("model.onnx", sha256(payload).hexdigest()),),
        raising=False,
    )

    def cached_snapshot(
        *, repo_id: str, revision: str, cache_dir: str, allow_patterns: list[str]
    ) -> str:
        assert repo_id == "Xenova/multilingual-e5-small"
        assert revision == "761b726dd34fb83930e26aab4e9ac3899aa1fa78"
        assert cache_dir == str(tmp_path)
        assert allow_patterns == ["model.onnx"]
        return str(tmp_path)

    monkeypatch.setattr(huggingface_hub, "snapshot_download", cached_snapshot)
    # When preparing a model, then corrupt cached bytes are rejected.
    if tampered:
        with pytest.raises(RuntimeError, match="SHA256"):
            _ = semantic_embeddings.verified_model_path(str(tmp_path))
    else:
        assert semantic_embeddings.verified_model_path(str(tmp_path)) == tmp_path


def test_integrity_failure_prevents_native_load_and_retains_lexical_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from datetime import UTC, datetime  # noqa: PLC0415
    from typing import Never  # noqa: PLC0415

    from fastembed import TextEmbedding  # noqa: PLC0415

    from dapa_morning_brief.models import Article, Section  # noqa: PLC0415
    from dapa_morning_brief.semantic_deduplication import (  # noqa: PLC0415
        create_semantic_index,
    )

    # Given failed integrity verification and a native constructor tripwire.
    _ = reload(semantic_embeddings)

    def reject_artifact(cache_dir: str) -> Never:
        assert cache_dir
        raise semantic_embeddings.ModelIntegrityError(tmp_path / "model.onnx")

    def forbidden_load(_self: TextEmbedding, **_kwargs: str | int) -> Never:
        message = "Native model constructor must not run for unverified bytes"
        raise AssertionError(message)

    monkeypatch.setattr(semantic_embeddings, "verified_model_path", reject_artifact)
    monkeypatch.setattr(TextEmbedding, "__init__", forbidden_load)
    articles = (
        Article("first", "a", datetime(2026, 1, 1, tzinfo=UTC), "news", Section.POLICY),
        Article(
            "second", "b", datetime(2026, 1, 1, tzinfo=UTC), "news", Section.POLICY
        ),
    )
    # When the real model boundary rejects the artifact.
    index = create_semantic_index(articles, ())
    # Then no native load occurs and lexical matching remains available.
    assert index.scored_articles == 0
    assert "lexical matching retained" in caplog.text
