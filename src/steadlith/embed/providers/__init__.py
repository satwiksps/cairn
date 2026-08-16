"""Built-in and optional embedding providers."""

from __future__ import annotations

from steadlith.config import EmbeddingConfig
from steadlith.embed.base import EmbeddingProvider
from steadlith.embed.providers.hash import HashEmbeddingProvider
from steadlith.errors import ConfigError


def create_provider(config: EmbeddingConfig) -> EmbeddingProvider:
    config.validate()
    if config.provider == "hash":
        return HashEmbeddingProvider(model=config.model, dimensions=config.dimensions)
    if config.provider == "openai":
        from steadlith.embed.providers.openai import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(
            model=config.model,
            dimensions=config.dimensions,
            api_key_env=config.api_key_env or "OPENAI_API_KEY",
            base_url=config.base_url,
        )
    if config.provider == "sentence-transformers":
        from steadlith.embed.providers.sentence_transformers import (
            SentenceTransformersProvider,
        )

        return SentenceTransformersProvider(model=config.model, dimensions=config.dimensions)
    raise ConfigError(f"Unknown embedding provider: {config.provider!r}")


__all__ = ["HashEmbeddingProvider", "create_provider"]
