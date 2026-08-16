"""Conformance surface for vector index backends."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class VectorMatch:
    score: float
    chunk_hash: str
    text: str
    document_id: str
    start_offset: int
    end_offset: int
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class IndexStatus:
    corpus_root: str | None
    generation: int
    documents: int
    active_chunks: int
    tombstoned_chunks: int
    hard_cuts: int
    total_boundaries: int
    model_id: str | None
    params_hash: str | None

    @property
    def hard_cut_rate(self) -> float:
        return self.hard_cuts / self.total_boundaries if self.total_boundaries else 0.0


@dataclass(frozen=True)
class ActiveRecord:
    instance_id: str
    document_id: str
    position: int
    chunk_hash: str
    text: str
    start_offset: int
    end_offset: int
    token_count: int
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class IndexRecord(ActiveRecord):
    vector: Sequence[float]


@dataclass(frozen=True)
class DocumentState:
    document_id: str
    root_hash: str
    chunk_count: int
    hard_cuts: int
    metadata: Mapping[str, Any]


class IndexAdapter(Protocol):
    """Minimum behavior every Steadlith vector backend must provide."""

    supports_metadata_filtering: bool

    def status(self) -> IndexStatus: ...

    def active_records(self) -> tuple[IndexRecord, ...]: ...

    def query(
        self,
        vector: Sequence[float],
        *,
        limit: int = 10,
        expected_model_id: str | None = None,
        expected_params_hash: str | None = None,
    ) -> list[VectorMatch]: ...

    def compact(self, *, before: str | None = None, dry_run: bool = False) -> int: ...

    def verify(self) -> tuple[bool, tuple[str, ...]]: ...
