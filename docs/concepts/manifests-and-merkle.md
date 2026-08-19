# Manifests and Merkle roots

A manifest records the desired content state without storing vectors. Its roots provide deterministic identifiers for document and corpus state.

## Document manifest

A document manifest contains:

- schema version;
- document ID;
- ordered chunk records;
- document metadata;
- chunker ID;
- chunker parameter hash;
- normalizer version;
- computed document root.

Each chunk record contains:

- chunk hash;
- start and end source offsets;
- deterministic token count;
- boundary and source metadata not already represented by reserved fields.

All chunks in one document manifest must carry the same chunker, parameter, and normalizer identity. Mixed identities are rejected.

## Document Merkle tree

Ordered chunk hashes become domain-separated leaf hashes. Adjacent nodes are combined upward. When a level has an odd final node, the parent construction records an empty right input instead of duplicating the node.

The empty document has one defined empty-root value. Order is significant:

```text
[hash_A, hash_B] != [hash_B, hash_A]
```

The tree can compare equal-sized states while pruning equal subtrees. A root match with the same leaf count means the ordered chunk-hash sequence matches.

## Corpus manifest

A corpus manifest maps document IDs to document manifests. For each document, Steadlith hashes the ordered pair `(document_id, document_root)`. These values, sorted by document ID, form the corpus Merkle tree.

The corpus root changes when:

- a document is added or removed;
- a document ID changes;
- an ordered document chunk hash changes;
- chunk order changes.

It does not change for offsets or filesystem metadata alone when ordered chunk hashes remain the same. The separate generation counter protects same-root transactions such as metadata moves and model migrations.

## Authoritative and mirror copies

The serialized manifest stored inside SQLite is authoritative. After an index transaction commits, Steadlith writes a formatted JSON mirror beside the database:

```text
.steadlith/index.sqlite3.manifest.json
```

The mirror is intended for inspection, backup checks, and diffs. It is excluded from source discovery so indexing cannot ingest its own changing output.

If mirror writing fails after commit, the CLI reports that the index committed. Run `verify` against SQLite before retrying.

## Root and generation

Use both values as a state token:

| State change | Corpus root | Generation |
| --- | --- | --- |
| No-op plan | Same | Same |
| Text or chunk-order change | Usually changes | Increments on apply |
| Metadata-only move | Can remain same | Increments |
| Embedding-model migration | Same | Increments |
| Delete then restore same content | Can return to earlier root | Continues increasing |

This is why stale-write checks cannot rely on the root alone.

## Serialization checks

Manifest deserialization validates schema versions, record types, and declared roots. Unknown persisted schema versions fail closed.

The JSON representation is deterministic for the same manifest, but consumers should not derive application authorization from a root alone. A root proves equality under the specified hash domains, not source trust or operator intent.
