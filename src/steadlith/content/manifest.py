"""Pure JSON-serializable manifests for indexed document and corpus state."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from steadlith.content.merkle import corpus_root, document_root
from steadlith.models import Chunk, ChunkRecord

MANIFEST_SCHEMA_VERSION = 1


def _metadata(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return {str(key): item for key, item in value.items()}


@dataclass(frozen=True)
class DocumentManifest:
    document_id: str
    chunks: tuple[ChunkRecord, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict, compare=False)
    chunker_id: str = ""
    chunker_params_hash: str = ""
    normalizer_version: str = ""
    schema_version: int = MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.document_id:
            raise ValueError("document_id cannot be empty")
        if self.schema_version != MANIFEST_SCHEMA_VERSION:
            raise ValueError(f"unsupported manifest schema version: {self.schema_version}")
        object.__setattr__(self, "chunks", tuple(self.chunks))
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def root_hash(self) -> str:
        return document_root(record.chunk_hash for record in self.chunks)

    @property
    def document_root(self) -> str:
        return self.root_hash

    @property
    def chunk_hashes(self) -> tuple[str, ...]:
        return tuple(record.chunk_hash for record in self.chunks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "document_id": self.document_id,
            "root_hash": self.root_hash,
            "chunker_id": self.chunker_id,
            "chunker_params_hash": self.chunker_params_hash,
            "normalizer_version": self.normalizer_version,
            "metadata": dict(self.metadata),
            "chunks": [record.to_dict() for record in self.chunks],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> DocumentManifest:
        chunks_value = value.get("chunks", [])
        if not isinstance(chunks_value, list):
            raise ValueError("document manifest chunks must be a list")
        chunks: list[ChunkRecord] = []
        for item in chunks_value:
            if not isinstance(item, Mapping):
                raise ValueError("each chunk record must be a mapping")
            chunks.append(ChunkRecord.from_dict(item))
        manifest = cls(
            document_id=str(value["document_id"]),
            chunks=tuple(chunks),
            metadata=_metadata(value.get("metadata", {}), label="document metadata"),
            chunker_id=str(value.get("chunker_id", "")),
            chunker_params_hash=str(value.get("chunker_params_hash", "")),
            normalizer_version=str(value.get("normalizer_version", "")),
            schema_version=int(value.get("schema_version", MANIFEST_SCHEMA_VERSION)),
        )
        declared_root = value.get("root_hash")
        if declared_root is not None and str(declared_root) != manifest.root_hash:
            raise ValueError("document manifest root hash does not match its chunks")
        return manifest

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":") if indent is None else None,
            indent=indent,
            allow_nan=False,
        )

    @classmethod
    def from_json(cls, value: str | bytes | bytearray) -> DocumentManifest:
        decoded = json.loads(value)
        if not isinstance(decoded, Mapping):
            raise ValueError("document manifest JSON must contain an object")
        return cls.from_dict(decoded)


@dataclass(frozen=True)
class CorpusManifest:
    documents: Mapping[str, DocumentManifest] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict, compare=False)
    schema_version: int = MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != MANIFEST_SCHEMA_VERSION:
            raise ValueError(f"unsupported manifest schema version: {self.schema_version}")
        documents = dict(self.documents)
        for document_id, manifest in documents.items():
            if document_id != manifest.document_id:
                raise ValueError("corpus document key must match manifest.document_id")
        object.__setattr__(self, "documents", documents)
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def document_roots(self) -> dict[str, str]:
        return {
            document_id: self.documents[document_id].root_hash
            for document_id in sorted(self.documents)
        }

    @property
    def root_hash(self) -> str:
        return corpus_root(self.document_roots)

    @property
    def corpus_root(self) -> str:
        return self.root_hash

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "root_hash": self.root_hash,
            "metadata": dict(self.metadata),
            "documents": {
                document_id: self.documents[document_id].to_dict()
                for document_id in sorted(self.documents)
            },
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> CorpusManifest:
        documents_value = value.get("documents", {})
        if not isinstance(documents_value, Mapping):
            raise ValueError("corpus manifest documents must be a mapping")
        documents: dict[str, DocumentManifest] = {}
        for document_id, item in documents_value.items():
            if not isinstance(item, Mapping):
                raise ValueError("each document manifest must be a mapping")
            documents[str(document_id)] = DocumentManifest.from_dict(item)
        manifest = cls(
            documents=documents,
            metadata=_metadata(value.get("metadata", {}), label="corpus metadata"),
            schema_version=int(value.get("schema_version", MANIFEST_SCHEMA_VERSION)),
        )
        declared_root = value.get("root_hash")
        if declared_root is not None and str(declared_root) != manifest.root_hash:
            raise ValueError("corpus manifest root hash does not match its documents")
        return manifest

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":") if indent is None else None,
            indent=indent,
            allow_nan=False,
        )

    @classmethod
    def from_json(cls, value: str | bytes | bytearray) -> CorpusManifest:
        decoded = json.loads(value)
        if not isinstance(decoded, Mapping):
            raise ValueError("corpus manifest JSON must contain an object")
        return cls.from_dict(decoded)

    def with_document(self, manifest: DocumentManifest) -> CorpusManifest:
        documents = dict(self.documents)
        documents[manifest.document_id] = manifest
        return replace(self, documents=documents)

    def without_document(self, document_id: str) -> CorpusManifest:
        documents = dict(self.documents)
        documents.pop(document_id, None)
        return replace(self, documents=documents)


def manifest_from_chunks(
    document_id: str,
    chunks: Iterable[Chunk],
    *,
    metadata: Mapping[str, Any] | None = None,
) -> DocumentManifest:
    values = tuple(chunks)
    identities = {
        (
            str(chunk.metadata.get("chunker_id", "")),
            str(chunk.metadata.get("chunker_params_hash", "")),
            str(chunk.metadata.get("normalizer_version", "")),
        )
        for chunk in values
    }
    if len(identities) > 1:
        raise ValueError(
            "all chunks in a document manifest must share chunker, parameters, "
            "and normalizer identity"
        )
    records = tuple(ChunkRecord.from_chunk(chunk) for chunk in values)
    first_metadata = values[0].metadata if values else {}
    return DocumentManifest(
        document_id=document_id,
        chunks=records,
        metadata=dict(metadata or {}),
        chunker_id=str(first_metadata.get("chunker_id", "")),
        chunker_params_hash=str(first_metadata.get("chunker_params_hash", "")),
        normalizer_version=str(first_metadata.get("normalizer_version", "")),
    )
