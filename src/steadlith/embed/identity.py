"""Pure embedding cache identity helpers (no SDK import or credentials)."""

from __future__ import annotations

import hashlib
import json

from steadlith._legacy_wire import V1_EMBEDDING_PARAMS_PREFIX
from steadlith.config import EmbeddingConfig


def embedding_identity(config: EmbeddingConfig) -> tuple[str, str]:
    config.validate()
    model_id = f"{config.provider}:{config.model}"
    payload: dict[str, object] = {
        "dimensions": config.dimensions,
        "model": config.model,
        "provider": config.provider,
    }
    if config.provider == "hash":
        payload["version"] = 1
    elif config.provider == "openai":
        payload["base_url"] = config.base_url or "https://api.openai.com/v1"
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    params_hash = hashlib.sha256(V1_EMBEDDING_PARAMS_PREFIX + serialized).hexdigest()
    return model_id, params_hash
