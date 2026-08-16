"""Small, dependency-free data models shared by Steadlith's pure core."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, overload


@dataclass
class Chunk:
    """A text chunk compatible with LangChain's ``Document`` shape.

    Steadlith intentionally depends only on the two attributes used by document
    consumers: ``page_content`` and ``metadata``.  Keeping this as a native
    model avoids importing a framework in the chunking core.
    """

    page_content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return self.page_content

    @property
    def start_offset(self) -> int:
        return int(self.metadata.get("start_offset", 0))

    @property
    def end_offset(self) -> int:
        return int(self.metadata.get("end_offset", self.start_offset))

    @property
    def token_count(self) -> int:
        return int(self.metadata.get("token_count", 0))

    @property
    def chunk_hash(self) -> str:
        return str(self.metadata.get("chunk_hash", ""))


@dataclass(frozen=True)
class ChunkRecord:
    """The compact per-chunk record stored in a document manifest."""

    chunk_hash: str
    start_offset: int
    end_offset: int
    token_count: int
    metadata: Mapping[str, Any] = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        if not self.chunk_hash:
            raise ValueError("chunk_hash cannot be empty")
        if self.start_offset < 0:
            raise ValueError("start_offset cannot be negative")
        if self.end_offset < self.start_offset:
            raise ValueError("end_offset cannot precede start_offset")
        if self.token_count < 0:
            raise ValueError("token_count cannot be negative")
        object.__setattr__(self, "metadata", dict(self.metadata))

    @classmethod
    def from_chunk(cls, chunk: Chunk) -> ChunkRecord:
        reserved = {"chunk_hash", "start_offset", "end_offset", "token_count"}
        metadata = {key: value for key, value in chunk.metadata.items() if key not in reserved}
        return cls(
            chunk_hash=chunk.chunk_hash,
            start_offset=chunk.start_offset,
            end_offset=chunk.end_offset,
            token_count=chunk.token_count,
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_hash": self.chunk_hash,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "token_count": self.token_count,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> ChunkRecord:
        metadata = value.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("chunk record metadata must be a mapping")
        return cls(
            chunk_hash=str(value["chunk_hash"]),
            start_offset=int(value["start_offset"]),
            end_offset=int(value["end_offset"]),
            token_count=int(value["token_count"]),
            metadata=dict(metadata),
        )


@dataclass(frozen=True)
class ChunkingStats:
    """Diagnostics from one deterministic chunking run."""

    chunk_count: int = 0
    total_tokens: int = 0
    primary_boundaries: int = 0
    backup_boundaries: int = 0
    hard_cuts: int = 0
    snapped_boundaries: int = 0
    token_counts: tuple[int, ...] = ()

    @property
    def hard_cut_rate(self) -> float:
        decisions = self.primary_boundaries + self.backup_boundaries + self.hard_cuts
        return self.hard_cuts / decisions if decisions else 0.0


@dataclass(frozen=True)
class ChunkingResult(Sequence[Chunk]):
    """Chunks plus diagnostics; behaves as a read-only chunk sequence."""

    chunks: tuple[Chunk, ...]
    stats: ChunkingStats

    def __iter__(self) -> Iterator[Chunk]:
        return iter(self.chunks)

    @overload
    def __getitem__(self, index: int) -> Chunk: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[Chunk]: ...

    def __getitem__(self, index: int | slice) -> Chunk | Sequence[Chunk]:
        return self.chunks[index]

    def __len__(self) -> int:
        return len(self.chunks)

    @classmethod
    def from_chunks(
        cls, chunks: Iterable[Chunk], *, stats: ChunkingStats | None = None
    ) -> ChunkingResult:
        values = tuple(chunks)
        if stats is None:
            counts = tuple(chunk.token_count for chunk in values)
            stats = ChunkingStats(
                chunk_count=len(values), total_tokens=sum(counts), token_counts=counts
            )
        return cls(values, stats)
