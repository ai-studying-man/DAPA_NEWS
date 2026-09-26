# Exception declarations verified against ONNX Runtime 1.30.0 native extension.
# Preserve the third-party names rather than changing their Error suffixes.
class DeviceReset(Exception): ...  # noqa: N818
class EngineError(Exception): ...
class EPFail(Exception): ...  # noqa: N818
class Fail(Exception): ...  # noqa: N818
class InvalidArgument(Exception): ...  # noqa: N818
class InvalidGraph(Exception): ...  # noqa: N818
class InvalidProtobuf(Exception): ...  # noqa: N818
class ModelLoadCanceled(Exception): ...  # noqa: N818
class ModelLoaded(Exception): ...  # noqa: N818
class ModelRequiresCompilation(Exception): ...  # noqa: N818
class NoModel(Exception): ...  # noqa: N818
class NoSuchFile(Exception): ...  # noqa: N818
class NotFound(Exception): ...  # noqa: N818
class NotImplemented(Exception): ...  # noqa: A001, N818
class RuntimeException(Exception): ...  # noqa: N818
