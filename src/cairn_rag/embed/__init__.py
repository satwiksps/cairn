"""Embedding provider interfaces and crash-resumable batching."""

from cairn_rag.embed.base import EmbeddingProvider
from cairn_rag.embed.batch import BatchResult, EmbeddingInput, embed_texts, embed_with_cache
from cairn_rag.embed.identity import embedding_identity
from cairn_rag.embed.providers import create_provider

__all__ = [
    "BatchResult",
    "EmbeddingInput",
    "EmbeddingProvider",
    "create_provider",
    "embedding_identity",
    "embed_texts",
    "embed_with_cache",
]
