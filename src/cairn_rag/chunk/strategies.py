"""Pure baseline chunking strategies used by Cairn's comparisons."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol

from cairn_rag.chunk.cdc import CDCChunker
from cairn_rag.chunk.params import CDCParams
from cairn_rag.chunk.stream import (
    NORMALIZER_VERSION,
    NormalizedStream,
    TokenCounter,
    normalize_stream,
    resolve_tokenizer_id,
)
from cairn_rag.content.hashing import canonical_json_hash, chunk_content_hash
from cairn_rag.models import Chunk

SimilarityFunction = Callable[[str, str], float]


class Chunker(Protocol):
    def split(self, text: str, metadata: Mapping[str, Any] | None = None) -> list[Chunk]: ...


def _end_at_token_limit(stream: NormalizedStream, start: int, limit: int) -> int:
    word_tokens = stream[start].token_count
    if word_tokens > limit:
        raise ValueError(
            f"word at index {start} has token count {word_tokens}, which exceeds max_tokens={limit}"
        )
    end = bisect_right(stream.token_prefix, stream.token_prefix[start] + limit, lo=start + 1) - 1
    if end <= start:  # pragma: no cover - guarded by the oversized-word check above
        raise AssertionError("token-limit search failed to make progress")
    return min(len(stream), end)


def _matches_recursive_separator(stream: NormalizedStream, position: int, separator: str) -> bool:
    if separator == "\n\n":
        return stream.is_paragraph_break(position)
    if separator == ". ":
        # Preserve the established default's sentence-boundary behavior,
        # including !, ?, and closing punctuation handled by the stream.
        return stream.is_sentence_break(position)
    if not separator:
        return True
    boundary_text = "\n\n" if stream.is_paragraph_break(position) else " "
    return f"{stream[position - 1].text}{boundary_text}".endswith(separator)


def _make_chunks(
    stream: NormalizedStream,
    ranges: Sequence[tuple[int, int]],
    *,
    chunker_id: str,
    params: Mapping[str, Any],
    metadata: Mapping[str, Any] | None,
) -> list[Chunk]:
    params_hash = canonical_json_hash(params, domain="cairn-chunker-params-v1")
    base_metadata = dict(metadata or {})
    result: list[Chunk] = []
    for index, (start, end) in enumerate(ranges):
        if end <= start:
            continue
        text = stream.text_between(start, end)
        source_start, source_end = stream.source_offsets(start, end)
        values = dict(base_metadata)
        values.update(
            {
                "chunk_hash": chunk_content_hash(
                    text,
                    chunker_id=chunker_id,
                    chunker_params_hash=params_hash,
                    normalizer_version=NORMALIZER_VERSION,
                ),
                "start_offset": source_start,
                "end_offset": source_end,
                "token_count": stream.tokens_between(start, end),
                "start_word": start,
                "end_word": end,
                "chunk_index": index,
                "chunker_id": chunker_id,
                "chunker_params_hash": params_hash,
                "normalizer_version": NORMALIZER_VERSION,
            }
        )
        result.append(Chunk(text, values))
    return result


class FixedChunker:
    """Fixed-token baseline; downstream boundaries drift after early edits."""

    def __init__(
        self,
        chunk_size_tokens: int = 512,
        overlap_tokens: int = 0,
        token_counter: TokenCounter | None = None,
        tokenizer_id: str | None = None,
    ) -> None:
        if chunk_size_tokens < 1:
            raise ValueError("chunk_size_tokens must be positive")
        if not 0 <= overlap_tokens < chunk_size_tokens:
            raise ValueError("overlap_tokens must be non-negative and smaller than chunk size")
        self.chunk_size_tokens = chunk_size_tokens
        self.overlap_tokens = overlap_tokens
        self.token_counter = token_counter
        self.tokenizer_id = resolve_tokenizer_id(token_counter, tokenizer_id)

    def split(self, text: str, metadata: Mapping[str, Any] | None = None) -> list[Chunk]:
        stream = normalize_stream(
            text,
            self.token_counter,
            tokenizer_id=self.tokenizer_id,
        )
        ranges: list[tuple[int, int]] = []
        start = 0
        while start < len(stream):
            end = _end_at_token_limit(stream, start, self.chunk_size_tokens)
            ranges.append((start, end))
            if end == len(stream):
                break
            next_start = end
            while (
                next_start > start + 1
                and stream.tokens_between(next_start - 1, end) <= self.overlap_tokens
            ):
                next_start -= 1
            start = next_start
        return _make_chunks(
            stream,
            ranges,
            chunker_id="fixed",
            params={
                "normalizer_version": NORMALIZER_VERSION,
                "tokenizer_id": self.tokenizer_id,
                "chunk_size_tokens": self.chunk_size_tokens,
                "overlap_tokens": self.overlap_tokens,
            },
            metadata=metadata,
        )

    def split_text(self, text: str) -> list[str]:
        return [chunk.page_content for chunk in self.split(text)]


class RecursiveChunker:
    """Paragraph/sentence/word recursive baseline with hard token bounds."""

    def __init__(
        self,
        max_tokens: int = 512,
        min_tokens: int = 1,
        separators: Sequence[str] = ("\n\n", ". ", " "),
        token_counter: TokenCounter | None = None,
        tokenizer_id: str | None = None,
    ) -> None:
        if not 1 <= min_tokens <= max_tokens:
            raise ValueError("sizes must satisfy 1 <= min_tokens <= max_tokens")
        if not separators:
            raise ValueError("separators cannot be empty")
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.separators = tuple(separators)
        self.token_counter = token_counter
        self.tokenizer_id = resolve_tokenizer_id(token_counter, tokenizer_id)

    def split(self, text: str, metadata: Mapping[str, Any] | None = None) -> list[Chunk]:
        stream = normalize_stream(
            text,
            self.token_counter,
            tokenizer_id=self.tokenizer_id,
        )
        ranges: list[tuple[int, int]] = []
        start = 0
        while start < len(stream):
            maximum = _end_at_token_limit(stream, start, self.max_tokens)
            if maximum == len(stream):
                ranges.append((start, maximum))
                break
            minimum = start + 1
            while minimum < maximum and stream.tokens_between(start, minimum) < self.min_tokens:
                minimum += 1
            end = maximum
            for separator in self.separators:
                candidates = [
                    position
                    for position in range(minimum, maximum + 1)
                    if _matches_recursive_separator(stream, position, separator)
                ]
                if candidates:
                    end = candidates[-1]
                    break
            ranges.append((start, end))
            start = end
        return _make_chunks(
            stream,
            ranges,
            chunker_id="recursive",
            params={
                "normalizer_version": NORMALIZER_VERSION,
                "tokenizer_id": self.tokenizer_id,
                "max_tokens": self.max_tokens,
                "min_tokens": self.min_tokens,
                "separators": self.separators,
            },
            metadata=metadata,
        )

    def split_text(self, text: str) -> list[str]:
        return [chunk.page_content for chunk in self.split(text)]


def lexical_similarity(left: str, right: str) -> float:
    left_words = {word.casefold() for word in left.split()}
    right_words = {word.casefold() for word in right.split()}
    if not left_words and not right_words:
        return 1.0
    union = left_words | right_words
    return len(left_words & right_words) / len(union) if union else 1.0


class SemanticChunker:
    """Semantic-style sentence-grouping baseline with an injectable similarity metric.

    The default is deterministic lexical Jaccard similarity so the core stays
    offline and dependency-free. Built-in reports label it as a lexical proxy;
    benchmarks may inject embedding similarity for a genuinely semantic run.
    """

    def __init__(
        self,
        max_tokens: int = 512,
        min_tokens: int = 64,
        similarity_threshold: float = 0.15,
        similarity_fn: SimilarityFunction | None = None,
        token_counter: TokenCounter | None = None,
        tokenizer_id: str | None = None,
    ) -> None:
        if not 1 <= min_tokens <= max_tokens:
            raise ValueError("sizes must satisfy 1 <= min_tokens <= max_tokens")
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be between zero and one")
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.similarity_threshold = similarity_threshold
        self.similarity_fn = similarity_fn or lexical_similarity
        self.token_counter = token_counter
        self.tokenizer_id = resolve_tokenizer_id(token_counter, tokenizer_id)

    def split(self, text: str, metadata: Mapping[str, Any] | None = None) -> list[Chunk]:
        stream = normalize_stream(
            text,
            self.token_counter,
            tokenizer_id=self.tokenizer_id,
        )
        sentence_ends = sorted(
            {
                position
                for position in range(1, len(stream) + 1)
                if stream.is_sentence_break(position)
                or stream.is_paragraph_break(position)
                or position == len(stream)
            }
        )
        ranges: list[tuple[int, int]] = []
        start = 0
        previous_unit_start = 0
        for unit_end in sentence_ends:
            if stream.tokens_between(start, unit_end) > self.max_tokens:
                while start < previous_unit_start:
                    # Do not let a hard split of the previous structural unit
                    # consume words from the current unit.  Otherwise ``start``
                    # can jump past later entries in ``sentence_ends`` and the
                    # next iteration attempts an invalid reversed stream slice.
                    hard_end = min(
                        _end_at_token_limit(stream, start, self.max_tokens),
                        previous_unit_start,
                    )
                    ranges.append((start, hard_end))
                    start = hard_end
                if start == previous_unit_start and start < unit_end:
                    maximum = _end_at_token_limit(stream, start, self.max_tokens)
                    if maximum < unit_end:
                        ranges.append((start, maximum))
                        start = maximum
            if (
                previous_unit_start > start
                and stream.tokens_between(start, previous_unit_start) >= self.min_tokens
            ):
                left = stream.text_between(start, previous_unit_start)
                right = stream.text_between(previous_unit_start, unit_end)
                if self.similarity_fn(left, right) < self.similarity_threshold:
                    ranges.append((start, previous_unit_start))
                    start = previous_unit_start
            previous_unit_start = unit_end
        while start < len(stream):
            end = _end_at_token_limit(stream, start, self.max_tokens)
            ranges.append((start, end))
            start = end
        return _make_chunks(
            stream,
            ranges,
            chunker_id="semantic",
            params={
                "normalizer_version": NORMALIZER_VERSION,
                "tokenizer_id": self.tokenizer_id,
                "max_tokens": self.max_tokens,
                "min_tokens": self.min_tokens,
                "similarity_threshold": self.similarity_threshold,
                "similarity_id": getattr(
                    self.similarity_fn, "__name__", type(self.similarity_fn).__name__
                ),
            },
            metadata=metadata,
        )

    def split_text(self, text: str) -> list[str]:
        return [chunk.page_content for chunk in self.split(text)]


def create_chunker(strategy: str = "cdc-rabin", **kwargs: Any) -> Chunker:
    """Construct a strategy by its stable configuration identifier."""

    if strategy in {"cdc-rabin", "cdc-rabin+snap"}:
        token_counter = kwargs.pop("token_counter", None)
        tokenizer_id = kwargs.pop("tokenizer_id", None)
        params_value = kwargs.pop("params", None)
        if params_value is not None and kwargs:
            raise TypeError("pass either params or CDC parameter keywords, not both")
        if params_value is None:
            if tokenizer_id is not None:
                kwargs["tokenizer_id"] = tokenizer_id
            params = CDCParams(**kwargs)
            tokenizer_override = None
        elif isinstance(params_value, CDCParams):
            params = params_value
            tokenizer_override = tokenizer_id
        elif isinstance(params_value, Mapping):
            if any(not isinstance(key, str) for key in params_value):
                raise TypeError("params mapping keys must be strings")
            allowed = set(CDCParams.__dataclass_fields__) | {"strategy"}
            unknown = set(params_value) - allowed
            if unknown:
                names = ", ".join(sorted(unknown))
                raise TypeError(f"unknown CDC params: {names}")
            params = CDCParams.from_mapping(params_value)
            tokenizer_override = tokenizer_id
        else:
            raise TypeError("params must be a CDCParams instance or mapping")
        params = params.with_snapping(strategy == "cdc-rabin+snap")
        return CDCChunker(
            params,
            token_counter,
            tokenizer_id=tokenizer_override,
        )
    params_value = kwargs.pop("params", None)
    if params_value is not None:
        if kwargs:
            raise TypeError("pass either params or strategy parameter keywords, not both")
        if not isinstance(params_value, Mapping):
            raise TypeError("params must be a mapping for non-CDC strategies")
        if any(not isinstance(key, str) for key in params_value):
            raise TypeError("params mapping keys must be strings")
        kwargs = {str(key): value for key, value in params_value.items()}
        configured_strategy = kwargs.pop("strategy", strategy)
        if str(configured_strategy) != strategy:
            raise ValueError("params strategy conflicts with the requested strategy")
    if strategy == "fixed":
        return FixedChunker(**kwargs)
    if strategy == "recursive":
        return RecursiveChunker(**kwargs)
    if strategy == "semantic":
        return SemanticChunker(**kwargs)
    raise ValueError(f"unknown chunking strategy: {strategy!r}")


def _config_value(config: object, name: str, default: object) -> object:
    if isinstance(config, Mapping):
        return config.get(name, default)
    return getattr(config, name, default)


def _config_int(config: object, name: str, default: int) -> int:
    value = _config_value(config, name, default)
    if not isinstance(value, (str, bytes, bytearray, int, float)):
        raise TypeError(f"{name} must be an integer")
    return int(value)


def chunker_from_config(
    config: object,
    token_counter: TokenCounter | None = None,
    *,
    tokenizer_id: str | None = None,
) -> Chunker:
    if isinstance(config, Mapping) and "chunker" in config:
        chunker = config["chunker"]
    else:
        chunker = getattr(config, "chunker", config)
    strategy = str(_config_value(chunker, "strategy", "cdc-rabin"))
    configured_tokenizer_id = _config_value(chunker, "tokenizer_id", None)
    resolved_tokenizer_id = (
        tokenizer_id
        if tokenizer_id is not None
        else str(configured_tokenizer_id)
        if configured_tokenizer_id is not None
        else None
    )
    if strategy in {"cdc-rabin", "cdc-rabin+snap"}:
        return CDCChunker(
            CDCParams.from_config(chunker),
            token_counter,
            tokenizer_id=tokenizer_id,
        )
    max_tokens = _config_int(chunker, "max_tokens", 512)
    min_tokens = _config_int(chunker, "min_tokens", 1)
    if strategy == "fixed":
        chunk_size_tokens = _config_int(chunker, "chunk_size_tokens", max_tokens)
        overlap_tokens = _config_int(chunker, "overlap_tokens", 0)
        return FixedChunker(
            chunk_size_tokens,
            overlap_tokens,
            token_counter=token_counter,
            tokenizer_id=resolved_tokenizer_id,
        )
    if strategy == "recursive":
        separators = _config_value(chunker, "separators", ("\n\n", ". ", " "))
        if not isinstance(separators, Sequence) or isinstance(separators, str):
            raise TypeError("recursive separators must be a sequence of strings")
        return RecursiveChunker(
            max_tokens,
            min_tokens,
            tuple(str(separator) for separator in separators),
            token_counter=token_counter,
            tokenizer_id=resolved_tokenizer_id,
        )
    if strategy == "semantic":
        return SemanticChunker(
            max_tokens,
            min_tokens,
            token_counter=token_counter,
            tokenizer_id=resolved_tokenizer_id,
        )
    raise ValueError(f"unknown chunking strategy: {strategy!r}")


def fixed_chunks(text: str, chunk_size_tokens: int = 512) -> list[Chunk]:
    return FixedChunker(chunk_size_tokens).split(text)


def recursive_chunks(text: str, max_tokens: int = 512) -> list[Chunk]:
    return RecursiveChunker(max_tokens).split(text)


def semantic_chunks(text: str, max_tokens: int = 512) -> list[Chunk]:
    return SemanticChunker(max_tokens).split(text)


STRATEGIES = ("fixed", "recursive", "semantic", "cdc-rabin", "cdc-rabin+snap")
