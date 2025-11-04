"""Deterministic 64-bit Rabin-style CDC with TTTD boundary selection."""

from __future__ import annotations

import hashlib
from bisect import bisect_right
from collections.abc import Mapping, Sequence
from dataclasses import replace
from functools import partial
from typing import Any

from cairn_rag.chunk.params import CHUNKER_ID, CDCParams
from cairn_rag.chunk.snap import snap_boundary_details
from cairn_rag.chunk.stream import (
    DEFAULT_TOKENIZER_ID,
    NormalizedStream,
    TokenCounter,
    normalize_stream,
    resolve_tokenizer_id,
)
from cairn_rag.content.hashing import chunk_content_hash
from cairn_rag.models import Chunk, ChunkingResult, ChunkingStats

UINT64_MASK = (1 << 64) - 1
RABIN_BASE = 0x100000001B3


def _word_symbol(text: str, paragraph_before: bool) -> int:
    marker = b"P" if paragraph_before else b"W"
    digest = hashlib.blake2b(marker + text.encode("utf-8"), digest_size=8, person=b"cairn-word-v1")
    return int.from_bytes(digest.digest(), "big")


class RabinRollingHash:
    """A fixed-window Rabin-Karp polynomial fingerprint modulo ``2**64``."""

    __slots__ = ("_base", "_hash", "_high", "_values", "_window_size")

    def __init__(self, window_size: int, *, base: int = RABIN_BASE) -> None:
        if window_size < 1:
            raise ValueError("window_size must be positive")
        if base <= 1 or base & 1 == 0:
            raise ValueError("base must be an odd integer greater than one")
        self._window_size = window_size
        self._base = base & UINT64_MASK
        self._high = pow(self._base, window_size - 1, 1 << 64)
        self._hash = 0
        self._values: list[int] = []

    @property
    def value(self) -> int:
        return self._hash

    @property
    def ready(self) -> bool:
        return len(self._values) == self._window_size

    def push(self, value: int) -> int | None:
        value &= UINT64_MASK
        if len(self._values) < self._window_size:
            self._values.append(value)
            self._hash = ((self._hash * self._base) + value) & UINT64_MASK
        else:
            outgoing = self._values.pop(0)
            self._values.append(value)
            self._hash = (self._hash - (outgoing * self._high)) & UINT64_MASK
            self._hash = ((self._hash * self._base) + value) & UINT64_MASK
        return self._hash if self.ready else None


def rolling_fingerprints(stream: NormalizedStream, window_words: int) -> tuple[int | None, ...]:
    """Return fingerprints indexed by boundary position (0 through word count)."""

    rolling = RabinRollingHash(window_words)
    values: list[int | None] = [None]
    for word in stream:
        values.append(rolling.push(_word_symbol(word.text, word.paragraph_before)))
    return tuple(values)


def _max_end(stream: NormalizedStream, start: int, max_tokens: int) -> int:
    word_tokens = stream[start].token_count
    if word_tokens > max_tokens:
        raise ValueError(
            f"word at index {start} has token count {word_tokens}, "
            f"which exceeds max_tokens={max_tokens}"
        )
    target = stream.token_prefix[start] + max_tokens
    end = bisect_right(stream.token_prefix, target, lo=start + 1) - 1
    if end <= start:  # pragma: no cover - guarded by the oversized-word check above
        raise AssertionError("token-limit search failed to make progress")
    return min(end, len(stream))


def _resolve_settings(
    params: CDCParams | None,
    token_counter: TokenCounter | None,
    tokenizer_id: str | None,
) -> CDCParams:
    settings = params or CDCParams()
    if tokenizer_id is not None:
        if params is not None and settings.tokenizer_id not in {DEFAULT_TOKENIZER_ID, tokenizer_id}:
            raise ValueError("tokenizer_id conflicts with params.tokenizer_id")
        settings = replace(settings, tokenizer_id=tokenizer_id)
    resolve_tokenizer_id(token_counter, settings.tokenizer_id)
    return settings


def _valid_snap_position(
    stream: NormalizedStream, settings: CDCParams, start: int, position: int
) -> bool:
    return (
        position > start
        and settings.min_tokens <= stream.tokens_between(start, position) <= settings.max_tokens
    )


def chunk_stream(
    stream: NormalizedStream,
    params: CDCParams | None = None,
    *,
    metadata: Mapping[str, Any] | None = None,
) -> ChunkingResult:
    """Split an already-normalized stream without performing I/O."""

    settings = params or CDCParams()
    if stream.normalizer_version != settings.normalizer_version:
        raise ValueError("stream and chunker normalizer versions differ")
    if stream.tokenizer_id != settings.tokenizer_id:
        raise ValueError("stream and chunker tokenizer identities differ")
    fingerprints = rolling_fingerprints(stream, settings.window_words)
    chunks: list[Chunk] = []
    primary_count = backup_count = hard_count = snapped_count = 0
    start = 0
    base_metadata = dict(metadata or {})

    while start < len(stream):
        maximum_end = _max_end(stream, start, settings.max_tokens)
        backup: int | None = None
        primary: int | None = None
        for position in range(start + 1, maximum_end + 1):
            token_count = stream.tokens_between(start, position)
            if token_count < settings.min_tokens:
                continue
            fingerprint = fingerprints[position]
            if fingerprint is None:
                continue
            if fingerprint & settings.backup_mask == 0:
                backup = position
            if fingerprint & settings.primary_mask == 0:
                primary = position
                break

        if primary is not None:
            raw_end = primary
            boundary_kind = "primary"
        elif maximum_end == len(stream):
            raw_end = len(stream)
            boundary_kind = "final"
        elif backup is not None:
            raw_end = backup
            boundary_kind = "backup"
        else:
            raw_end = maximum_end
            boundary_kind = "hard"

        end = raw_end
        snap_kind = "raw"
        if settings.snap_to_boundaries and raw_end < len(stream):
            snapped = snap_boundary_details(
                raw_end,
                stream,
                settings.snap_window_words,
                is_valid=partial(_valid_snap_position, stream, settings, start),
            )
            end = snapped.position
            snap_kind = snapped.kind
            snapped_count += int(snapped.snapped)

        if end <= start:  # Defensive guard: validators should make this unreachable.
            end = min(start + 1, len(stream))
            boundary_kind = "hard"

        if boundary_kind == "primary":
            primary_count += 1
        elif boundary_kind == "backup":
            backup_count += 1
        elif boundary_kind == "hard":
            hard_count += 1

        chunk_text = stream.text_between(start, end)
        start_offset, end_offset = stream.source_offsets(start, end)
        token_count = stream.tokens_between(start, end)
        content_hash = chunk_content_hash(
            chunk_text,
            chunker_id=CHUNKER_ID,
            chunker_params_hash=settings.params_hash,
            normalizer_version=settings.normalizer_version,
        )
        chunk_metadata = dict(base_metadata)
        chunk_metadata.update(
            {
                "chunk_hash": content_hash,
                "start_offset": start_offset,
                "end_offset": end_offset,
                "token_count": token_count,
                "start_word": start,
                "end_word": end,
                "raw_end_word": raw_end,
                "chunk_index": len(chunks),
                "chunker_id": CHUNKER_ID,
                "chunker_params_hash": settings.params_hash,
                "normalizer_version": settings.normalizer_version,
                "boundary_kind": boundary_kind,
                "snap_kind": snap_kind,
            }
        )
        chunks.append(Chunk(chunk_text, chunk_metadata))
        start = end

    token_counts = tuple(chunk.token_count for chunk in chunks)
    stats = ChunkingStats(
        chunk_count=len(chunks),
        total_tokens=stream.token_count,
        primary_boundaries=primary_count,
        backup_boundaries=backup_count,
        hard_cuts=hard_count,
        snapped_boundaries=snapped_count,
        token_counts=token_counts,
    )
    return ChunkingResult(tuple(chunks), stats)


def chunk_text(
    text: str,
    params: CDCParams | None = None,
    *,
    token_counter: TokenCounter | None = None,
    tokenizer_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ChunkingResult:
    settings = _resolve_settings(params, token_counter, tokenizer_id)
    stream = normalize_stream(
        text,
        token_counter,
        tokenizer_id=settings.tokenizer_id,
    )
    return chunk_stream(stream, settings, metadata=metadata)


class CDCChunker:
    """Framework-neutral, LangChain-compatible content-defined chunker."""

    def __init__(
        self,
        params: CDCParams | None = None,
        token_counter: TokenCounter | None = None,
        *,
        tokenizer_id: str | None = None,
    ) -> None:
        self.params = _resolve_settings(params, token_counter, tokenizer_id)
        self.token_counter = token_counter
        self.last_stats = ChunkingStats()

    @classmethod
    def from_config(
        cls,
        config: object,
        token_counter: TokenCounter | None = None,
        *,
        tokenizer_id: str | None = None,
    ) -> CDCChunker:
        return cls(
            CDCParams.from_config(config),
            token_counter,
            tokenizer_id=tokenizer_id,
        )

    def split_with_stats(
        self, text: str, metadata: Mapping[str, Any] | None = None
    ) -> ChunkingResult:
        result = chunk_text(text, self.params, token_counter=self.token_counter, metadata=metadata)
        self.last_stats = result.stats
        return result

    def split(self, text: str, metadata: Mapping[str, Any] | None = None) -> list[Chunk]:
        return list(self.split_with_stats(text, metadata).chunks)

    def split_text(self, text: str) -> list[str]:
        return [chunk.page_content for chunk in self.split(text)]

    @property
    def hard_cut_count(self) -> int:
        return self.last_stats.hard_cuts


def boundary_positions(chunks: Sequence[Chunk]) -> tuple[int, ...]:
    return tuple(int(chunk.metadata["end_word"]) for chunk in chunks)
