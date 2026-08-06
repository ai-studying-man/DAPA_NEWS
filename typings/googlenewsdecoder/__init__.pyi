from typing import TypedDict

class DecodeResult(TypedDict, total=False):
    status: bool
    decoded_url: str
    message: str

def gnewsdecoder(
    source_url: str,
    interval: int | None = ...,
    proxy: str | None = ...,
) -> DecodeResult: ...
