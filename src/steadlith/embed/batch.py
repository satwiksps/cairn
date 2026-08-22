"""Batching with cache-first resume semantics."""

from __future__ import annotations

import math
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from steadlith.embed.base import EmbeddingProvider
from steadlith.errors import BackendError, ProviderError, TransientProviderError
from steadlith.store.cache import Cache


@dataclass(frozen=True)
class EmbeddingInput:
    chunk_hash: str
    text: str
    token_count: int


@dataclass(frozen=True)
class BatchResult:
    vectors: Mapping[str, tuple[float, ...]]
    cache_hits: int
    embedded: int
    embedded_tokens: int


def _batches(items: list[EmbeddingInput], size: int) -> Iterable[list[EmbeddingInput]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def embed_texts(
    texts: Sequence[str],
    *,
    provider: EmbeddingProvider,
    max_retries: int = 3,
) -> list[tuple[float, ...]]:
    """Embed one provider batch with validation and bounded transient retries."""

    if type(max_retries) is not int or max_retries < 0:
        raise ValueError("max_retries must be a non-negative integer")
    if not texts:
        return []
    try:
        model_id = provider.model_id
        params_hash = provider.params_hash
        dimensions = provider.dimensions
    except Exception as exc:
        raise ProviderError(f"Could not read provider identity: {exc}") from exc
    if not isinstance(model_id, str) or not model_id:
        raise ProviderError("Provider model_id must be a non-empty string")
    if not isinstance(params_hash, str) or not params_hash:
        raise ProviderError("Provider params_hash must be a non-empty string")
    if type(dimensions) is not int or dimensions <= 0:
        raise ProviderError("Provider dimensions must be a positive integer")

    attempt = 0
    while True:
        try:
            raw_vectors = provider.embed(texts)
            break
        except TransientProviderError:
            attempt += 1
            if attempt > max_retries:
                raise
            time.sleep(min(2 ** (attempt - 1), 8))
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"Embedding provider failed unexpectedly: {exc}") from exc

    try:
        identity_changed = (
            provider.model_id != model_id
            or provider.params_hash != params_hash
            or provider.dimensions != dimensions
        )
    except Exception as exc:
        raise ProviderError(f"Could not revalidate provider identity: {exc}") from exc
    if identity_changed:
        raise ProviderError("Embedding provider identity changed during a batch")

    try:
        vector_rows = list(raw_vectors)
    except TypeError as exc:
        raise ProviderError("Provider returned a non-iterable embedding response") from exc
    if len(vector_rows) != len(texts):
        raise ProviderError(f"Provider returned {len(vector_rows)} vectors for {len(texts)} inputs")
    try:
        vectors = [tuple(float(value) for value in vector) for vector in vector_rows]
    except (TypeError, ValueError, OverflowError) as exc:
        raise ProviderError(f"Provider returned a non-numeric vector: {exc}") from exc
    if any(len(vector) != dimensions for vector in vectors):
        raise ProviderError("Provider returned an unexpected vector dimension")
    if any(not math.isfinite(value) for vector in vectors for value in vector):
        raise ProviderError("Provider returned a non-finite vector")
    return vectors


def embed_with_cache(
    records: Iterable[EmbeddingInput],
    *,
    cache: Cache,
    provider: EmbeddingProvider,
    batch_size: int = 64,
    max_retries: int = 3,
) -> BatchResult:
    """Resolve unique chunks cache-first and persist each completed provider batch.

    Writing the cache after every successful batch is intentional: if the process is
    killed after that commit, the next run reuses those embeddings. A provider can still
    charge twice if the process dies after the provider accepts a request but before the
    corresponding cache commit; strict spend idempotency requires provider support.
    Index visibility is handled separately in one adapter transaction.
    """

    if type(batch_size) is not int or batch_size <= 0:
        raise ValueError("batch_size must be positive")
    if type(max_retries) is not int or max_retries < 0:
        raise ValueError("max_retries must be a non-negative integer")
    unique: dict[str, EmbeddingInput] = {}
    for record in records:
        if not isinstance(record.chunk_hash, str) or not record.chunk_hash:
            raise ValueError("embedding input chunk_hash must be a non-empty string")
        if not isinstance(record.text, str):
            raise ValueError("embedding input text must be a string")
        if type(record.token_count) is not int or record.token_count < 0:
            raise ValueError("embedding input token_count must be a non-negative integer")
        previous = unique.get(record.chunk_hash)
        if previous is not None and (
            previous.text != record.text or previous.token_count != record.token_count
        ):
            raise ValueError(
                f"duplicate chunk hash {record.chunk_hash!r} has incompatible input content"
            )
        unique[record.chunk_hash] = record
    try:
        model_id = provider.model_id
        params_hash = provider.params_hash
        dimensions = provider.dimensions
    except Exception as exc:
        raise ProviderError(f"Could not read embedding provider identity: {exc}") from exc
    if not isinstance(model_id, str) or not model_id:
        raise ProviderError("Provider model_id must be a non-empty string")
    if not isinstance(params_hash, str) or not params_hash:
        raise ProviderError("Provider params_hash must be a non-empty string")
    if type(dimensions) is not int or dimensions <= 0:
        raise ProviderError("Provider dimensions must be a positive integer")

    vectors: dict[str, tuple[float, ...]] = {}
    missing: list[EmbeddingInput] = []
    cache_keys = {chunk_hash: (chunk_hash, model_id, params_hash) for chunk_hash in unique}
    cached_vectors = cache.get_many(cache_keys.values())
    for record in unique.values():
        vector = cached_vectors.get(cache_keys[record.chunk_hash])
        if vector is None:
            missing.append(record)
        else:
            if len(vector) != dimensions:
                raise BackendError(
                    f"Cached vector for chunk {record.chunk_hash!r} has {len(vector)} "
                    f"dimensions; provider identity requires {dimensions}"
                )
            if any(not math.isfinite(value) for value in vector):
                raise BackendError(f"Cached vector for chunk {record.chunk_hash!r} is not finite")
            vectors[record.chunk_hash] = vector
    cache_hits = len(vectors)
    embedded_tokens = 0
    for batch in _batches(missing, batch_size):
        new_vectors = embed_texts(
            [record.text for record in batch],
            provider=provider,
            max_retries=max_retries,
        )
        try:
            identity_changed = (
                provider.model_id != model_id
                or provider.params_hash != params_hash
                or provider.dimensions != dimensions
            )
        except Exception as exc:
            raise ProviderError(f"Could not revalidate provider identity: {exc}") from exc
        if identity_changed:
            raise ProviderError("Embedding provider identity changed during a batch")
        cache.put_many(
            (
                record.chunk_hash,
                model_id,
                params_hash,
                vector,
                record.token_count,
            )
            for record, vector in zip(batch, new_vectors, strict=True)
        )
        for record, vector in zip(batch, new_vectors, strict=True):
            vectors[record.chunk_hash] = vector
            embedded_tokens += record.token_count
    return BatchResult(
        vectors=vectors,
        cache_hits=cache_hits,
        embedded=len(missing),
        embedded_tokens=embedded_tokens,
    )
