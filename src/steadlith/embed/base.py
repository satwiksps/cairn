"""Minimal provider protocol shared by optional embedding integrations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class EmbeddingProvider(Protocol):
    """A provider adapter with a stable cache identity."""

    @property
    def model_id(self) -> str: ...

    @property
    def params_hash(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]: ...
