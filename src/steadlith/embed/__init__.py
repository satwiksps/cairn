"""Embedding provider interfaces and crash-resumable batching."""

from steadlith.embed.base import EmbeddingProvider
from steadlith.embed.batch import BatchResult, EmbeddingInput, embed_texts, embed_with_cache
from steadlith.embed.identity import embedding_identity
from steadlith.embed.providers import create_provider

__all__ = [
    "BatchResult",
    "EmbeddingInput",
    "EmbeddingProvider",
    "create_provider",
    "embedding_identity",
    "embed_texts",
    "embed_with_cache",
]
