from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

import pytest

from steadlith.embed.batch import EmbeddingInput, embed_texts, embed_with_cache
from steadlith.embed.providers.hash import HashEmbeddingProvider
from steadlith.errors import BackendError, ProviderError, TransientProviderError
from steadlith.store import Cache


def test_batches_resume_from_content_addressed_cache(tmp_path: Path) -> None:
    provider = HashEmbeddingProvider(dimensions=16)
    records = [
        EmbeddingInput("a", "alpha beta", 2),
        EmbeddingInput("b", "beta gamma", 2),
    ]
    with Cache(tmp_path / "cache.sqlite3") as cache:
        first = embed_with_cache(records, cache=cache, provider=provider, batch_size=1)
        second = embed_with_cache(records, cache=cache, provider=provider, batch_size=1)
    assert first.embedded == 2
    assert first.cache_hits == 0
    assert second.embedded == 0
    assert second.cache_hits == 2
    for chunk_hash in first.vectors:
        assert second.vectors[chunk_hash] == pytest.approx(first.vectors[chunk_hash])


def test_duplicate_chunk_hash_is_embedded_once(tmp_path: Path) -> None:
    provider = HashEmbeddingProvider(dimensions=8)
    records = [
        EmbeddingInput("same", "same text", 2),
        EmbeddingInput("same", "same text", 2),
    ]
    with Cache(tmp_path / "cache.sqlite3") as cache:
        result = embed_with_cache(records, cache=cache, provider=provider)
    assert result.embedded == 1
    assert list(result.vectors) == ["same"]


def test_duplicate_chunk_hash_cannot_alias_different_content(tmp_path: Path) -> None:
    provider = HashEmbeddingProvider(dimensions=8)
    records = [
        EmbeddingInput("same", "first text", 2),
        EmbeddingInput("same", "different text", 2),
    ]
    with Cache(tmp_path / "cache.sqlite3") as cache:
        with pytest.raises(ValueError, match="incompatible input content"):
            embed_with_cache(records, cache=cache, provider=provider)


class MalformedProvider:
    model_id = "test:malformed"
    params_hash = "params"
    dimensions = 1

    def embed(self, texts: Sequence[str]) -> list[tuple[object, ...]]:
        return [(None,) for _ in texts]


def test_malformed_provider_vectors_raise_typed_error(tmp_path: Path) -> None:
    with Cache(tmp_path / "cache.sqlite3") as cache:
        with pytest.raises(ProviderError, match="non-numeric vector"):
            embed_with_cache(
                [EmbeddingInput("chunk", "text", 1)],
                cache=cache,
                provider=MalformedProvider(),  # type: ignore[arg-type]
            )


class MissingResponseProvider:
    model_id = "test:missing"
    params_hash = "params"
    dimensions = 1

    def embed(self, texts: Sequence[str]) -> None:
        del texts
        return None


def test_non_iterable_provider_response_raises_typed_error(tmp_path: Path) -> None:
    with Cache(tmp_path / "cache.sqlite3") as cache:
        with pytest.raises(ProviderError, match="non-iterable"):
            embed_with_cache(
                [EmbeddingInput("chunk", "text", 1)],
                cache=cache,
                provider=MissingResponseProvider(),  # type: ignore[arg-type]
            )


class MutableIdentityProvider:
    dimensions = 1
    params_hash = "params"

    def __init__(self) -> None:
        self.model_id = "test:first"

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        self.model_id = "test:changed"
        return [(1.0,) for _ in texts]


def test_provider_identity_cannot_change_mid_batch(tmp_path: Path) -> None:
    with Cache(tmp_path / "cache.sqlite3") as cache:
        with pytest.raises(ProviderError, match="identity changed"):
            embed_with_cache(
                [EmbeddingInput("chunk", "text", 1)],
                cache=cache,
                provider=MutableIdentityProvider(),
            )
        assert cache.stats().entries == 0


def test_cached_vector_dimension_must_match_provider_identity(tmp_path: Path) -> None:
    provider = HashEmbeddingProvider(dimensions=8)
    with Cache(tmp_path / "cache.sqlite3") as cache:
        cache.put("chunk", provider.model_id, provider.params_hash, (1.0,), token_count=1)
        with pytest.raises(BackendError, match="provider identity requires 8"):
            embed_with_cache([EmbeddingInput("chunk", "text", 1)], cache=cache, provider=provider)


class PermanentFailureProvider:
    model_id = "test:permanent"
    params_hash = "params"
    dimensions = 1

    def __init__(self) -> None:
        self.calls = 0

    def embed(self, texts: Sequence[str]) -> NoReturn:
        del texts
        self.calls += 1
        raise ProviderError("invalid request")


def test_permanent_provider_errors_are_not_retried(tmp_path: Path) -> None:
    provider = PermanentFailureProvider()
    with Cache(tmp_path / "cache.sqlite3") as cache:
        with pytest.raises(ProviderError, match="invalid request"):
            embed_with_cache(
                [EmbeddingInput("chunk", "text", 1)],
                cache=cache,
                provider=provider,
                max_retries=5,
            )
    assert provider.calls == 1


class TransientThenSuccessProvider:
    model_id = "test:transient"
    params_hash = "params"
    dimensions = 1

    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        self.calls += 1
        if self.calls <= self.failures:
            raise TransientProviderError("retryable failure")
        return [(float(index),) for index, _text in enumerate(texts)]


def test_transient_provider_errors_retry_until_success(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = TransientThenSuccessProvider(failures=2)
    delays: list[float] = []
    monkeypatch.setattr("steadlith.embed.batch.time.sleep", delays.append)

    assert embed_texts(["text"], provider=provider, max_retries=2) == [(0.0,)]
    assert provider.calls == 3
    assert delays == [1, 2]


def test_transient_provider_errors_stop_after_retry_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = TransientThenSuccessProvider(failures=3)
    delays: list[float] = []
    monkeypatch.setattr("steadlith.embed.batch.time.sleep", delays.append)

    with pytest.raises(TransientProviderError, match="retryable failure"):
        embed_texts(["text"], provider=provider, max_retries=2)
    assert provider.calls == 3
    assert delays == [1, 2]


class StaticResponseProvider:
    model_id = "test:static"
    params_hash = "params"
    dimensions = 1

    def __init__(self, vectors: list[tuple[float, ...]]) -> None:
        self.vectors = vectors

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        del texts
        return self.vectors


@pytest.mark.parametrize("vectors", [[], [(1.0,), (2.0,)]])
def test_provider_vector_count_must_match_input_count(
    vectors: list[tuple[float, ...]],
) -> None:
    with pytest.raises(ProviderError, match=r"returned \d+ vectors for 1 inputs"):
        embed_texts(["text"], provider=StaticResponseProvider(vectors))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_provider_vectors_must_be_finite(value: float) -> None:
    with pytest.raises(ProviderError, match="non-finite vector"):
        embed_texts(["text"], provider=StaticResponseProvider([(value,)]))
