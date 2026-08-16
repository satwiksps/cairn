"""Frozen v1 wire identifiers retained for persisted-state compatibility.

These values are protocol data, not current product branding. Changing any of
them would invalidate v0.2 manifests, index records, cache keys, or vectors.
New code should import the narrowly named constant it needs instead of copying
these byte strings.
"""

from __future__ import annotations

LEGACY_CONFIG_FILENAME = "cairn.toml"
LEGACY_STATE_DIRECTORY = ".cairn"
LEGACY_HASH_MODEL = "cairn-hash-256-v1"
LEGACY_CACHE_PATH = ".cairn/cache.sqlite3"
LEGACY_INDEX_PATH = ".cairn/index.sqlite3"
LEGACY_SOURCE_EXCLUDE = ("**/drafts/**", "**/.git/**", "**/.cairn/**")

V1_IDENTITY_SCHEMA = "cairn-chunk-identity-v1"
V1_NORMALIZER = "cairn-normalizer-v1"

V1_BYTES_DOMAIN = "cairn-bytes-v1"
V1_TEXT_DOMAIN = "cairn-text-v1"
V1_JSON_DOMAIN = "cairn-json-v1"
V1_CHUNK_DOMAIN = "cairn-chunk-v1"
V1_CHUNKER_PARAMS_DOMAIN = "cairn-chunker-params-v1"
V1_MERKLE_EMPTY_DOMAIN = "cairn-merkle-empty-v1"
V1_MERKLE_LEAF_DOMAIN = "cairn-merkle-leaf-v1"
V1_MERKLE_NODE_DOMAIN = "cairn-merkle-node-v1"
V1_CORPUS_DOCUMENT_DOMAIN = "cairn-corpus-document-v1"
V1_INDEX_RECORD_DOMAIN = "cairn-index-record-v1"

V1_EMBEDDING_PARAMS_PREFIX = b"cairn:embedding-params:v1\0"
V1_INSTANCE_PREFIX = b"cairn:instance:v1\0"
V1_MEASURE_CHUNK_PREFIX = b"cairn:measure:chunk:v1\0"
V1_WORD_PERSON = b"cairn-word-v1"
V1_HASH_FEATURE_PERSON = b"cairn-hash-v1"

__all__ = [
    "LEGACY_CONFIG_FILENAME",
    "LEGACY_CACHE_PATH",
    "LEGACY_HASH_MODEL",
    "LEGACY_INDEX_PATH",
    "LEGACY_SOURCE_EXCLUDE",
    "LEGACY_STATE_DIRECTORY",
    "V1_BYTES_DOMAIN",
    "V1_CHUNK_DOMAIN",
    "V1_CHUNKER_PARAMS_DOMAIN",
    "V1_CORPUS_DOCUMENT_DOMAIN",
    "V1_EMBEDDING_PARAMS_PREFIX",
    "V1_HASH_FEATURE_PERSON",
    "V1_IDENTITY_SCHEMA",
    "V1_INDEX_RECORD_DOMAIN",
    "V1_INSTANCE_PREFIX",
    "V1_JSON_DOMAIN",
    "V1_MEASURE_CHUNK_PREFIX",
    "V1_MERKLE_EMPTY_DOMAIN",
    "V1_MERKLE_LEAF_DOMAIN",
    "V1_MERKLE_NODE_DOMAIN",
    "V1_NORMALIZER",
    "V1_TEXT_DOMAIN",
    "V1_WORD_PERSON",
]
