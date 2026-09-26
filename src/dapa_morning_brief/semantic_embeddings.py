"""Lazy CPU model adapter for multilingual article embeddings."""

from __future__ import annotations

import os
from functools import lru_cache
from hashlib import file_digest
from pathlib import Path
from typing import TYPE_CHECKING, Final

from pydantic import TypeAdapter

if TYPE_CHECKING:
    from fastembed import TextEmbedding

_MODEL_NAME: Final = "dapa-multilingual-e5-small"
# Upstream commit and LFS SHA256 verified via the Hugging Face model API.
# JSON digests were computed from this same immutable snapshot (2026-09-26).
_MODEL_REVISION: Final = "761b726dd34fb83930e26aab4e9ac3899aa1fa78"
_MODEL_FILES: Final = (
    (
        "onnx/model_quantized.onnx",
        "f80102d3f2a1229f387d3c81909990d8945513e347b0eab049f7de3c6f98c193",
    ),
    (
        "tokenizer.json",
        "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39",
    ),
    ("config.json", "cb99455288675345e1a4f411438d5d0adbba5fbd3a67ea4fb03c015433b996c1"),
    (
        "tokenizer_config.json",
        "a1d6bc8734a6f635dc158508bef000f8e2e5a759c7d92f984b2c86e5ff53425b",
    ),
    (
        "special_tokens_map.json",
        "d05497f1da52c5e09554c0cd874037a083e1dc1b9cfd48034d1c717f1afc07a7",
    ),
)
_VECTORS: Final = TypeAdapter(tuple[tuple[float, ...], ...])


class ModelIntegrityError(RuntimeError):
    """A downloaded or cached artifact does not match the reviewed snapshot."""

    def __init__(self, path: Path) -> None:
        """Identify the artifact rejected before native deserialization."""
        self.path: Path = path
        super().__init__(f"Model artifact SHA256 mismatch: {path}")


def verified_model_path(cache_dir: str) -> Path:
    """Download the pinned snapshot and verify every consumed file."""
    import huggingface_hub  # noqa: PLC0415

    snapshot = Path(
        huggingface_hub.snapshot_download(
            repo_id="Xenova/multilingual-e5-small",
            revision=_MODEL_REVISION,
            cache_dir=cache_dir,
            allow_patterns=[name for name, _ in _MODEL_FILES],
        )
    )
    for name, expected in _MODEL_FILES:
        path = snapshot / name
        with path.open("rb") as artifact:
            actual = file_digest(artifact, "sha256").hexdigest()
        if actual != expected:
            raise ModelIntegrityError(path)
    return snapshot


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    from fastembed import TextEmbedding  # noqa: PLC0415 - lazy optional runtime
    from fastembed.common.model_description import (  # noqa: PLC0415
        ModelSource,
        PoolingType,
    )

    if not any(
        model["model"] == _MODEL_NAME for model in TextEmbedding.list_supported_models()
    ):
        TextEmbedding.add_custom_model(
            model=_MODEL_NAME,
            pooling=PoolingType.MEAN,
            normalization=True,
            sources=ModelSource(hf="Xenova/multilingual-e5-small"),
            dim=384,
            model_file="onnx/model_quantized.onnx",
        )
    cache_dir = os.getenv("DAPA_EMBEDDING_CACHE", ".dapa-model-cache")
    model_path = verified_model_path(cache_dir)
    return TextEmbedding(
        model_name=_MODEL_NAME,
        threads=2,
        cache_dir=cache_dir,
        specific_model_path=str(model_path),
    )


def encode(texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
    """Materialize the lazy inference iterator at the failure boundary."""
    from onnxruntime.capi.onnxruntime_pybind11_state import (  # noqa: PLC0415
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
    from onnxruntime.capi.onnxruntime_pybind11_state import (  # noqa: PLC0415
        NotImplemented as OnnxNotImplemented,
    )

    try:
        return _VECTORS.validate_python(_model().embed(texts, batch_size=1))
    except (
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
    ) as error:
        raise RuntimeError(str(error)) from error
