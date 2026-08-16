"""Optional local sentence-transformers provider."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

from steadlith._legacy_wire import V1_EMBEDDING_PARAMS_PREFIX
from steadlith.errors import ProviderError


class SentenceTransformersProvider:
    def __init__(self, *, model: str, dimensions: int) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ProviderError(
                "Local model support is not installed; run "
                "'pip install steadlith[sentence-transformers]'"
            ) from exc
        self.model = model
        try:
            self._model: Any = SentenceTransformer(model)
            actual = int(self._model.get_sentence_embedding_dimension())
        except Exception as exc:
            raise ProviderError(f"Could not load local embedding model {model!r}: {exc}") from exc
        if actual <= 0:
            raise ProviderError(f"Local embedding model {model!r} reported invalid dimensions")
        if dimensions != actual:
            raise ProviderError(
                f"Configured dimensions {dimensions} do not match {model!r} ({actual})"
            )
        self._dimensions = actual
        payload = json.dumps(
            {"dimensions": actual, "model": model, "provider": "sentence-transformers"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self._params_hash = hashlib.sha256(V1_EMBEDDING_PARAMS_PREFIX + payload).hexdigest()

    @property
    def model_id(self) -> str:
        return f"sentence-transformers:{self.model}"

    @property
    def params_hash(self) -> str:
        return self._params_hash

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        if not texts:
            return []
        try:
            vectors = self._model.encode(
                list(texts), normalize_embeddings=True, show_progress_bar=False
            )
        except Exception as exc:
            raise ProviderError(f"Local embedding failed: {exc}") from exc
        return [tuple(float(value) for value in vector) for vector in vectors]
