"""Canonical, domain-separated content hashes used by Cairn."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

HASH_ALGORITHM = "sha256"
IDENTITY_SCHEMA_VERSION = "cairn-chunk-identity-v1"


def _field_bytes(value: str | bytes) -> bytes:
    return value if isinstance(value, bytes) else value.encode("utf-8")


def hash_fields(domain: str, fields: Iterable[str | bytes]) -> str:
    """Hash length-delimited fields, preventing concatenation ambiguity."""

    digest = hashlib.sha256()
    domain_bytes = domain.encode("ascii")
    digest.update(len(domain_bytes).to_bytes(4, "big"))
    digest.update(domain_bytes)
    for field in fields:
        encoded = _field_bytes(field)
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def hash_bytes(value: bytes, *, domain: str = "cairn-bytes-v1") -> str:
    return hash_fields(domain, (value,))


def hash_text(value: str, *, domain: str = "cairn-text-v1") -> str:
    return hash_fields(domain, (value,))


def canonical_json_hash(value: Mapping[str, Any], *, domain: str = "cairn-json-v1") -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hash_fields(domain, (encoded,))


def chunk_content_hash(
    chunk_text: str,
    *,
    chunker_id: str,
    chunker_params_hash: str,
    normalizer_version: str,
    identity_schema_version: str = IDENTITY_SCHEMA_VERSION,
) -> str:
    """Return a chunk identity independent of any embedding model.

    Embedding provider/model parameters deliberately do not appear in this
    interface.  They belong in the embedding-cache key alongside this hash.
    """

    if not chunker_id or not chunker_params_hash or not normalizer_version:
        raise ValueError("chunk identity fields cannot be empty")
    return hash_fields(
        "cairn-chunk-v1",
        (
            identity_schema_version,
            normalizer_version,
            chunker_id,
            chunker_params_hash,
            chunk_text,
        ),
    )


chunk_hash = chunk_content_hash
