# Chunk identity

Chunk identity is the foundation for reuse. It answers a precise question: under a versioned normalization and boundary configuration, is this canonical chunk content identical?

## Normalized word stream

Steadlith scans non-whitespace word spans from the original Python string and records half-open source offsets for each word.

Normalization performs:

- Unicode NFC normalization on each word;
- ordinary whitespace collapse to one space;
- paragraph-break preservation as an explicit double-newline marker;
- deterministic token counting with a versioned tokenizer identity.

Offsets continue to refer to the original unnormalized source string. The canonical chunk text is reconstructed from normalized words and paragraph markers.

The default tokenizer identity is `word-v1`, which assigns one size token per normalized word. It is a model-independent boundary unit, not a claim about provider token billing.

A custom token counter can be supplied through the Python API only with an explicit, non-default `tokenizer_id`. Since token counts affect boundaries, an ambiguous custom counter is rejected.

## Boundary identity

`CDCParams.params_hash` is SHA-256 over canonical JSON containing:

- window size;
- minimum and maximum token sizes;
- primary and backup mask bits;
- snapping radius and enabled state;
- normalizer version;
- tokenizer identity;
- rolling-hash identity;
- boundary-rule version.

Changing any field changes the parameter hash, even if one particular document happens to produce the same boundaries.

## Chunk hash

The v1 chunk hash is a domain-separated, length-delimited SHA-256 digest over:

```text
identity_schema_version
normalizer_version
chunker_id
chunker_params_hash
canonical_chunk_text
```

Length prefixes prevent ambiguity between adjacent fields. Domain separation prevents one type of stored hash from being interpreted as another.

The following are deliberately absent:

- embedding provider;
- embedding model;
- vector dimensions;
- source document path;
- source offsets;
- occurrence position;
- filesystem metadata.

This separation lets content identity remain stable when a model changes, while the embedding cache creates a new model-specific entry.

## Occurrence identity

An index occurrence is not identified by chunk hash alone. The same chunk can appear several times in one document or across documents.

The index assigns a generation-scoped instance ID using document, position, chunk hash, corpus root, and embedding scope. A removed occurrence is tombstoned. Restoring the same content in a later generation receives a new lifecycle ID rather than reactivating the old row.

## Stability contract

The v1 identity schema is frozen by golden-vector tests. Steadlith 0.3 preserves stored v1 domains from Cairn 0.2 so existing indexes and paid cache entries remain usable after explicit configuration adoption.

Some persisted metadata therefore contains an earlier internal wire identifier. It is immutable compatibility data, not an active package, command, configuration, or state-directory name.

An incompatible future algorithm must use a new identity version. It must not reinterpret existing v1 hashes.

## Practical consequences

Whitespace-only edits
: Ordinary whitespace changes within a paragraph can retain canonical text and chunk hashes. Adding or removing a paragraph boundary can change canonical text and snapping candidates.

Moving a paragraph
: The content hash can remain the same while offsets and occurrence position change. The plan can classify this as a move and reuse the embedding.

Renaming a source file
: Chunk hashes can remain the same, but the document ID and occurrence lifecycle change.

Changing a model
: Chunk hashes remain stable. Cache and active index embedding identity change.

Changing `max_tokens`
: Parameter hash changes for the entire strategy, so even textually identical output chunks receive the new identity.

## Inspect identity in Python

```python
from steadlith import CDCChunker

chunker = CDCChunker()
chunk = chunker.split("One paragraph.\n\nAnother paragraph.")[0]

print(chunk.chunk_hash)
print(chunk.metadata["chunker_id"])
print(chunk.metadata["chunker_params_hash"])
print(chunk.metadata["normalizer_version"])
```

Treat metadata identity fields as persisted protocol values. Do not rewrite them for display branding.
