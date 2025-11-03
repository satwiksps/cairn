from __future__ import annotations

import json

import pytest

from cairn_rag.chunk import CDCChunker, CDCParams
from cairn_rag.content import (
    CorpusManifest,
    DocumentManifest,
    MerkleTree,
    chunk_content_hash,
    corpus_root,
    manifest_from_chunks,
)


def test_chunk_hash_commits_to_chunking_but_not_embedding_model() -> None:
    fields = {
        "chunker_id": "cdc-rabin",
        "chunker_params_hash": "params",
        "normalizer_version": "normalizer-v1",
    }
    model_a = "embedding-a"
    model_b = "embedding-b"
    assert model_a != model_b
    first = chunk_content_hash("same content", **fields)
    second = chunk_content_hash("same content", **fields)
    assert first == second
    assert first != chunk_content_hash("changed content", **fields)
    assert first != chunk_content_hash(
        "same content", **{**fields, "chunker_params_hash": "other-params"}
    )


def test_merkle_roots_are_deterministic_order_sensitive_and_diffable() -> None:
    first = MerkleTree.from_leaves(["a", "b", "c", "d"])
    same = MerkleTree.from_leaves(["a", "b", "c", "d"])
    changed = MerkleTree.from_leaves(["a", "b", "different", "d"])
    reordered = MerkleTree.from_leaves(["b", "a", "c", "d"])

    assert first.root == same.root
    assert first.root != changed.root
    assert first.root != reordered.root
    assert first.diff_indices(changed) == (2,)
    assert MerkleTree.from_leaves([]).root == MerkleTree.from_leaves([]).root


def test_corpus_root_commits_to_document_ids_and_has_sorted_order() -> None:
    assert corpus_root({"b": "root-b", "a": "root-a"}) == corpus_root(
        [("a", "root-a"), ("b", "root-b")]
    )
    assert corpus_root({"a": "root-a"}) != corpus_root({"renamed": "root-a"})


def test_manifest_round_trip_and_tamper_detection() -> None:
    params = CDCParams(
        window_words=4,
        min_tokens=4,
        max_tokens=12,
        primary_mask_bits=3,
        backup_mask_bits=2,
    )
    chunks = CDCChunker(params).split("one two three four five six seven eight nine ten")
    document = manifest_from_chunks("manual", chunks, metadata={"path": "manual.md"})
    corpus = CorpusManifest({"manual": document}, metadata={"created_by": "test"})

    assert DocumentManifest.from_json(document.to_json()) == document
    assert CorpusManifest.from_json(corpus.to_json()) == corpus
    assert corpus.document_roots == {"manual": document.root_hash}
    assert json.loads(corpus.to_json())["root_hash"] == corpus.root_hash

    tampered = corpus.to_dict()
    tampered["documents"]["manual"]["chunks"][0]["chunk_hash"] = "tampered"
    with pytest.raises(ValueError, match="root hash"):
        CorpusManifest.from_dict(tampered)


def test_manifest_document_key_must_match_document_id() -> None:
    document = DocumentManifest("actual")
    with pytest.raises(ValueError, match="must match"):
        CorpusManifest({"wrong": document})


def test_manifest_rejects_chunks_with_mixed_chunking_identity() -> None:
    params = CDCParams(
        window_words=2,
        min_tokens=1,
        max_tokens=8,
        primary_mask_bits=2,
        backup_mask_bits=1,
    )
    raw = CDCChunker(params).split("one two three")[0]
    snapped = CDCChunker(params.with_snapping()).split("one two three")[0]

    with pytest.raises(ValueError, match="must share chunker"):
        manifest_from_chunks("mixed", [raw, snapped])
