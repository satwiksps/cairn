"""Stable public surface for Cairn's dependency-light core."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from cairn_rag.chunk.cdc import CDCChunker
from cairn_rag.chunk.params import CDCParams
from cairn_rag.models import Chunk
from cairn_rag.store import Cache

try:
    __version__ = version("cairn-rag")
except PackageNotFoundError:  # source checkout without an installed distribution
    __version__ = "0.2.0"

__all__ = ["CDCChunker", "CDCParams", "Cache", "Chunk", "__version__"]
