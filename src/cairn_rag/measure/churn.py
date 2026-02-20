"""Measure chunk churn after controlled document edits.

Chunk reuse is computed with a multiset, not a set.  This is important for
documents containing repeated boilerplate: each old occurrence can satisfy at
most one revised occurrence.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .corpora import (
    BUILTIN_CORPORA,
    CorpusFixture,
    EditOperation,
    iter_edit_cases,
)

DEFAULT_STRATEGY_NAMES: tuple[str, ...] = (
    "fixed",
    "recursive",
    "semantic-lexical-proxy",
    "cdc-rabin",
    "cdc-rabin+snap",
)


@runtime_checkable
class Chunker(Protocol):
    """The small boundary required from a benchmarked chunker."""

    def split(self, text: str, metadata: Mapping[str, Any] | None = None) -> Sequence[Any]: ...


@dataclass(frozen=True)
class EmbeddingPrice:
    """A caller-visible input-token price used for churn estimates.

    Prices change.  Cairn therefore keeps the quote and its label in the result
    rather than silently presenting a hard-coded value as current market data.
    """

    usd_per_million_tokens: float
    label: str = "caller-supplied"

    def __post_init__(self) -> None:
        if not math.isfinite(self.usd_per_million_tokens) or self.usd_per_million_tokens < 0:
            raise ValueError("usd_per_million_tokens must be finite and non-negative")
        if not self.label.strip():
            raise ValueError("price label must not be empty")

    def estimate(self, token_count: int) -> float:
        """Return the input cost for ``token_count`` in US dollars."""

        if token_count < 0:
            raise ValueError("token_count must be non-negative")
        return token_count * self.usd_per_million_tokens / 1_000_000

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation."""

        return {
            "usd_per_million_tokens": self.usd_per_million_tokens,
            "label": self.label,
        }


# This is an illustrative, versioned benchmark input rather than a claim about
# the current price of any provider.  CLI/reporting callers should pass a fresh
# published quote and preserve its source/as-of date in ``label``.
ILLUSTRATIVE_PRICE = EmbeddingPrice(
    usd_per_million_tokens=0.02,
    label="illustrative USD quote; replace with a current published provider price",
)


@dataclass(frozen=True)
class ChunkSnapshot:
    """The minimal immutable chunk data needed for a churn comparison."""

    chunk_hash: str
    text: str
    token_count: int

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation."""

        return {
            "chunk_hash": self.chunk_hash,
            "text": self.text,
            "token_count": self.token_count,
        }


@dataclass(frozen=True)
class ChurnResult:
    """Churn and estimated re-embedding cost for one edit."""

    strategy: str
    corpus_name: str
    document_id: str
    operation: EditOperation
    original_chunk_count: int
    revised_chunk_count: int
    reused_chunk_count: int
    chunks_to_embed: int
    chunks_removed: int
    tokens_to_embed: int
    reembed_fraction: float
    estimated_cost_usd: float
    price: EmbeddingPrice

    @property
    def reembed_percent(self) -> float:
        """The revised-chunk fraction expressed as a percentage."""

        return self.reembed_fraction * 100.0

    @property
    def reembed_count(self) -> int:
        """Alias spelling for callers presenting the changed chunk count."""

        return self.chunks_to_embed

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation suitable for CLI output."""

        return {
            "strategy": self.strategy,
            "corpus_name": self.corpus_name,
            "document_id": self.document_id,
            "operation": self.operation.value,
            "original_chunk_count": self.original_chunk_count,
            "revised_chunk_count": self.revised_chunk_count,
            "reused_chunk_count": self.reused_chunk_count,
            "chunks_to_embed": self.chunks_to_embed,
            "reembed_count": self.reembed_count,
            "chunks_removed": self.chunks_removed,
            "tokens_to_embed": self.tokens_to_embed,
            "reembed_fraction": self.reembed_fraction,
            "reembed_percent": self.reembed_percent,
            "estimated_cost_usd": self.estimated_cost_usd,
            "price": self.price.as_dict(),
        }

    def summary_row(self) -> dict[str, object]:
        """Return compact columns for a table renderer."""

        return {
            "strategy": self.strategy,
            "corpus": self.corpus_name,
            "edit": self.operation.value,
            "chunks": self.chunks_to_embed,
            "fraction": self.reembed_fraction,
            "tokens": self.tokens_to_embed,
            "cost_usd": self.estimated_cost_usd,
        }


@dataclass(frozen=True)
class ChurnSummary:
    """A deterministic collection of per-edit churn measurements."""

    results: tuple[ChurnResult, ...]
    fixture_notice: str = (
        "Built-in fixtures are smoke/regression data, not published real-corpus results."
    )

    @property
    def total_chunks_to_embed(self) -> int:
        return sum(result.chunks_to_embed for result in self.results)

    @property
    def total_estimated_cost_usd(self) -> float:
        return sum(result.estimated_cost_usd for result in self.results)

    def summary_rows(self) -> tuple[dict[str, object], ...]:
        """Return one compact, JSON-safe row per measurement."""

        return tuple(result.summary_row() for result in self.results)

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation suitable for CLI output."""

        return {
            "fixture_notice": self.fixture_notice,
            "total_chunks_to_embed": self.total_chunks_to_embed,
            "total_estimated_cost_usd": self.total_estimated_cost_usd,
            "results": [result.as_dict() for result in self.results],
        }


def _chunk_text(chunk: Any) -> str:
    if isinstance(chunk, str):
        return chunk
    for attribute in ("page_content", "text"):
        value = getattr(chunk, attribute, None)
        if isinstance(value, str):
            return value
    if isinstance(chunk, Mapping):
        for key in ("page_content", "text"):
            value = chunk.get(key)
            if isinstance(value, str):
                return value
    raise TypeError("chunk must be text or expose a string page_content/text value")


def _chunk_token_count(chunk: Any, text: str) -> int:
    value = getattr(chunk, "token_count", None)
    if value is None and isinstance(chunk, Mapping):
        value = chunk.get("token_count")
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    # Core's default counter is deliberately a deterministic word count.  The
    # benchmark fallback mirrors that behavior for third-party splitters.
    return len(text.split())


def _chunk_hash(chunk: Any, text: str) -> str:
    value = getattr(chunk, "chunk_hash", None)
    if value is None and isinstance(chunk, Mapping):
        value = chunk.get("chunk_hash")
    if isinstance(value, str) and value:
        return value
    return hashlib.sha256(b"cairn:measure:chunk:v1\0" + text.encode("utf-8")).hexdigest()


def snapshot_chunks(chunks: Iterable[Any]) -> tuple[ChunkSnapshot, ...]:
    """Normalize core, third-party, or string chunks for measurement."""

    snapshots: list[ChunkSnapshot] = []
    for chunk in chunks:
        text = _chunk_text(chunk)
        snapshots.append(
            ChunkSnapshot(
                chunk_hash=_chunk_hash(chunk, text),
                text=text,
                token_count=_chunk_token_count(chunk, text),
            )
        )
    return tuple(snapshots)


def split_for_measurement(chunker: Chunker, text: str) -> tuple[ChunkSnapshot, ...]:
    """Split text while tolerating splitters without a metadata argument."""

    try:
        chunks = chunker.split(text, metadata={"benchmark": True})
    except TypeError as metadata_error:
        try:
            chunks = chunker.split(text)
        except TypeError as no_metadata_error:
            raise metadata_error from no_metadata_error
    return snapshot_chunks(chunks)


def _added_snapshots(
    original: Sequence[ChunkSnapshot], revised: Sequence[ChunkSnapshot]
) -> tuple[ChunkSnapshot, ...]:
    remaining = Counter(chunk.chunk_hash for chunk in original)
    added: list[ChunkSnapshot] = []
    for chunk in revised:
        if remaining[chunk.chunk_hash] > 0:
            remaining[chunk.chunk_hash] -= 1
        else:
            added.append(chunk)
    return tuple(added)


def _result_from_snapshots(
    original_chunks: Sequence[ChunkSnapshot],
    revised_chunks: Sequence[ChunkSnapshot],
    *,
    strategy: str,
    operation: EditOperation,
    corpus_name: str,
    document_id: str,
    price: EmbeddingPrice,
) -> ChurnResult:
    original_counts = Counter(chunk.chunk_hash for chunk in original_chunks)
    revised_counts = Counter(chunk.chunk_hash for chunk in revised_chunks)
    reused = sum((original_counts & revised_counts).values())
    additions = _added_snapshots(original_chunks, revised_chunks)
    chunks_removed = sum((original_counts - revised_counts).values())
    tokens_to_embed = sum(chunk.token_count for chunk in additions)
    revised_count = len(revised_chunks)
    return ChurnResult(
        strategy=strategy,
        corpus_name=corpus_name,
        document_id=document_id,
        operation=operation,
        original_chunk_count=len(original_chunks),
        revised_chunk_count=revised_count,
        reused_chunk_count=reused,
        chunks_to_embed=len(additions),
        chunks_removed=chunks_removed,
        tokens_to_embed=tokens_to_embed,
        reembed_fraction=len(additions) / revised_count if revised_count else 0.0,
        estimated_cost_usd=price.estimate(tokens_to_embed),
        price=price,
    )


def measure_churn(
    original: str,
    revised: str,
    *,
    chunker: Chunker,
    strategy: str,
    operation: EditOperation | str,
    corpus_name: str = "custom",
    document_id: str = "document",
    price: EmbeddingPrice = ILLUSTRATIVE_PRICE,
) -> ChurnResult:
    """Measure multiset chunk churn for one original/revised pair.

    The fraction denominator is the revised chunk count: it answers what share
    of the resulting index needs an embedding call.  An empty revised document
    therefore has a defined fraction of zero and may still report removals.
    """

    if not strategy.strip():
        raise ValueError("strategy must not be empty")
    operation = EditOperation(operation)
    original_chunks = split_for_measurement(chunker, original)
    revised_chunks = split_for_measurement(chunker, revised)
    return _result_from_snapshots(
        original_chunks,
        revised_chunks,
        strategy=strategy,
        operation=operation,
        corpus_name=corpus_name,
        document_id=document_id,
        price=price,
    )


def measure_corpus_churn(
    corpus: CorpusFixture,
    *,
    chunker: Chunker,
    strategy: str,
    operation: EditOperation | str,
    price: EmbeddingPrice = ILLUSTRATIVE_PRICE,
    document_id: str | None = None,
) -> ChurnResult:
    """Measure an edit while including unchanged documents in the denominator."""

    if not strategy.strip():
        raise ValueError("strategy must not be empty")
    operation = EditOperation(operation)
    cases = {case.operation: case for case in iter_edit_cases(corpus, document_id=document_id)}
    case = cases[operation]
    original_chunks: list[ChunkSnapshot] = []
    revised_chunks: list[ChunkSnapshot] = []
    for document in corpus.documents:
        original_chunks.extend(split_for_measurement(chunker, document.text))
        revised_text = case.revised if document.document_id == case.document_id else document.text
        revised_chunks.extend(split_for_measurement(chunker, revised_text))
    return _result_from_snapshots(
        original_chunks,
        revised_chunks,
        strategy=strategy,
        operation=operation,
        corpus_name=corpus.name,
        document_id=case.document_id,
        price=price,
    )


def default_strategies() -> dict[str, Chunker]:
    """Construct the five built-in strategies with CI-sized parameters.

    Imports are local so users can use the fixture and metric primitives without
    importing Cairn's chunking implementation during module discovery.
    """

    from cairn_rag.chunk.cdc import CDCChunker
    from cairn_rag.chunk.params import CDCParams
    from cairn_rag.chunk.strategies import FixedChunker, RecursiveChunker, SemanticChunker

    return {
        "fixed": FixedChunker(chunk_size_tokens=48, overlap_tokens=0),
        "recursive": RecursiveChunker(max_tokens=64, min_tokens=16),
        "semantic-lexical-proxy": SemanticChunker(max_tokens=64, min_tokens=16),
        "cdc-rabin": CDCChunker(
            CDCParams(
                window_words=8,
                min_tokens=24,
                max_tokens=64,
                primary_mask_bits=5,
                backup_mask_bits=3,
                snap_window_words=8,
                snap_to_boundaries=False,
            )
        ),
        "cdc-rabin+snap": CDCChunker(
            CDCParams(
                window_words=8,
                min_tokens=24,
                max_tokens=64,
                primary_mask_bits=5,
                backup_mask_bits=3,
                snap_window_words=8,
                snap_to_boundaries=True,
            )
        ),
    }


def benchmark_churn(
    *,
    strategies: Mapping[str, Chunker] | None = None,
    corpora: Iterable[CorpusFixture] = BUILTIN_CORPORA,
    operations: Iterable[EditOperation | str] = tuple(EditOperation),
    price: EmbeddingPrice = ILLUSTRATIVE_PRICE,
) -> ChurnSummary:
    """Run the deterministic churn smoke/regression benchmark."""

    selected_strategies = dict(strategies) if strategies is not None else default_strategies()
    if not selected_strategies:
        raise ValueError("at least one strategy is required")
    requested_operations = tuple(EditOperation(operation) for operation in operations)
    if not requested_operations:
        raise ValueError("at least one edit operation is required")
    corpus_values = tuple(corpora)
    if not corpus_values:
        raise ValueError("at least one corpus is required")
    results: list[ChurnResult] = []
    for corpus in corpus_values:
        for strategy_name, chunker in selected_strategies.items():
            for operation in requested_operations:
                results.append(
                    measure_corpus_churn(
                        corpus,
                        chunker=chunker,
                        strategy=strategy_name,
                        operation=operation,
                        price=price,
                    )
                )
    return ChurnSummary(tuple(results))


__all__ = [
    "DEFAULT_STRATEGY_NAMES",
    "ILLUSTRATIVE_PRICE",
    "ChunkSnapshot",
    "Chunker",
    "ChurnResult",
    "ChurnSummary",
    "EmbeddingPrice",
    "benchmark_churn",
    "default_strategies",
    "measure_churn",
    "measure_corpus_churn",
    "snapshot_chunks",
    "split_for_measurement",
]
