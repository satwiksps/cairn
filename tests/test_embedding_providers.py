from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from cairn_rag.embed.providers.hash import HashEmbeddingProvider
from cairn_rag.embed.providers.openai import OpenAIEmbeddingProvider
from cairn_rag.embed.providers.sentence_transformers import SentenceTransformersProvider
from cairn_rag.errors import ProviderError, TransientProviderError


def test_hash_provider_rejects_unbounded_or_ambiguous_dimensions() -> None:
    with pytest.raises(ValueError, match="between 1"):
        HashEmbeddingProvider(dimensions=65_537)
    with pytest.raises(ValueError, match="between 1"):
        HashEmbeddingProvider(dimensions=True)  # type: ignore[arg-type]


def test_sentence_transformer_load_failures_are_typed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = ModuleType("sentence_transformers")

    class BrokenModel:
        def __init__(self, model: str) -> None:
            raise RuntimeError(f"cannot load {model}")

    module.SentenceTransformer = BrokenModel  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)

    with pytest.raises(ProviderError, match="Could not load local embedding model"):
        SentenceTransformersProvider(model="broken", dimensions=8)


def test_openai_client_initialization_failures_are_typed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = ModuleType("openai")

    class ConnectionFailure(Exception):
        pass

    class BrokenClient:
        def __init__(self, **kwargs: object) -> None:
            del kwargs
            raise RuntimeError("client initialization failed")

    module.APIConnectionError = ConnectionFailure  # type: ignore[attr-defined]
    module.APITimeoutError = ConnectionFailure  # type: ignore[attr-defined]
    module.OpenAI = BrokenClient  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openai", module)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with pytest.raises(ProviderError, match="Could not initialize"):
        OpenAIEmbeddingProvider(model="test", dimensions=8)


def test_openai_connection_failure_is_retryable() -> None:
    class ConnectionFailure(Exception):
        pass

    class Embeddings:
        def create(self, **kwargs: object) -> None:
            del kwargs
            raise ConnectionFailure("offline")

    provider = OpenAIEmbeddingProvider.__new__(OpenAIEmbeddingProvider)
    provider.model = "test"
    provider._dimensions = 8
    provider._transient_error_types = (ConnectionFailure,)
    provider._client = SimpleNamespace(embeddings=Embeddings())

    with pytest.raises(TransientProviderError, match="offline"):
        provider.embed(["query"])
