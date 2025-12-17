"""A deterministic, offline feature-hashing embedder for tests and evaluation."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass

from cairn_rag.config import MAX_VECTOR_DIMENSIONS

_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


def _params_hash(model: str, dimensions: int) -> str:
    payload = json.dumps(
        {"dimensions": dimensions, "model": model, "provider": "hash", "version": 1},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(b"cairn:embedding-params:v1\0" + payload).hexdigest()


@dataclass(frozen=True)
class HashEmbeddingProvider:
    """Signed feature hashing; useful for smoke tests, not production retrieval.

    It intentionally has no learned semantics. Keeping it built in makes the entire
    index/apply/delete path testable with no account, model download, or network.
    """

    model: str = "cairn-hash-256-v1"
    dimensions: int = 256

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("model must be a non-empty string")
        if type(self.dimensions) is not int or not 0 < self.dimensions <= MAX_VECTOR_DIMENSIONS:
            raise ValueError(
                f"dimensions must be an integer between 1 and {MAX_VECTOR_DIMENSIONS:,}"
            )

    @property
    def model_id(self) -> str:
        return f"hash:{self.model}"

    @property
    def params_hash(self) -> str:
        return _params_hash(self.model, self.dimensions)

    def _embed_one(self, text: str) -> tuple[float, ...]:
        tokens = [match.group(0).casefold() for match in _TOKEN_RE.finditer(text)]
        vector = [0.0] * self.dimensions
        features = list(tokens)
        features.extend(
            f"{left}\x1f{right}" for left, right in zip(tokens, tokens[1:], strict=False)
        )
        for feature in features:
            digest = hashlib.blake2b(
                feature.encode("utf-8"), digest_size=16, person=b"cairn-hash-v1"
            ).digest()
            index = int.from_bytes(digest[:8], "little") % self.dimensions
            sign = 1.0 if digest[8] & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return tuple(vector)

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        return [self._embed_one(text) for text in texts]
