# Vector adapter conformance

## Purpose

This document defines behavior that every Cairn vector-index adapter must demonstrate. It is backend-neutral: method names may differ, but observable semantics may not.

The key words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** describe conformance requirements. No adapter is considered supported merely because it can insert vectors.

## Capability declaration

An adapter exposes an immutable capability record at construction time:

| Capability | Meaning |
| --- | --- |
| metadata filtering | every normal query can enforce the active-record predicate |
| atomic batch | a batch is wholly visible or wholly absent |
| compare-and-swap state | commit can reject a stale expected manifest root |
| alias swap | a staged collection can become active atomically |
| physical delete | selected record occurrences can be permanently removed |
| deterministic iteration | records can be enumerated for verification in stable order |

Capabilities describe tested behavior for the connected backend/version, not SDK feature names. Unsupported capabilities must fail clearly; an adapter must not silently emulate stronger guarantees than it provides.

## Record model

Each indexed occurrence MUST preserve:

- a stable occurrence/vector identifier;
- `chunk_hash`;
- document and source identifiers;
- start/end offsets and token count;
- embedding model and parameter identities;
- `valid_from` and nullable `valid_to`;
- the manifest or apply-operation identity needed for idempotency.

Occurrence identity MUST distinguish duplicate text at different positions. Content identity may deduplicate embedding computation, but it cannot collapse two retrievable occurrences into one record without explicit semantics.

User metadata must be namespaced or validated so it cannot overwrite Cairn's reserved fields.

## Required behavior

### Idempotent upsert

Applying the same operation more than once MUST produce one logical record with the same metadata. A retry after an ambiguous timeout must not duplicate an active occurrence.

An upsert with a reused occurrence identifier but incompatible content/model identity MUST fail rather than mutate history silently.

### Active-only query

Every standard query path MUST exclude records whose `valid_to` is at or before the query's effective time. This predicate must be applied server-side when the backend supports it; post-filtering an already truncated top-k result is not conformant.

Adapters without reliable metadata filtering are **degraded**. They MUST say so during planning/application and MUST physically delete before reporting deletion success.

### Tombstone

Logical delete sets `valid_to` without removing history or changing the stored embedding. Repeating the same delete is idempotent. Attempting to tombstone a missing record is either a documented no-op or a typed conflict, consistently across runs.

After successful deletion, the occurrence MUST be unreachable through all public query methods, including fetch-by-filter and similarity search.

### Move

Moving unchanged content updates occurrence/source metadata without invoking the embedding provider. If the backend cannot update metadata safely, the adapter MAY stage a replacement record using the already cached embedding, but MUST preserve active-only visibility and idempotency.

### Commit and stale-plan protection

Apply MUST validate the expected old manifest root. Concurrently committed state causes a typed stale-plan conflict; last-writer-wins is not acceptable.

Where atomic batches are unavailable, an adapter MUST use a documented staging/reconciliation protocol and MUST NOT advance the durable manifest root until all required records are active and deletes are enforced.

### Verification

The adapter provides enough stable information to compare expected occurrence identities, content hashes, model identities, and active status with a manifest. Verification reports missing, unexpected, mismatched, and still-active-deleted records separately.

### Compaction

Compaction physically removes only tombstones older than the requested cutoff/rollback window. It is idempotent and never removes an active record. A dry-run reports eligible counts without mutation.

### Errors and secrets

Backend failures map to Cairn's typed adapter errors while preserving the original exception as a cause. Messages may contain safe record identifiers but MUST NOT expose credentials, source text, complete vectors, or connection-string secrets.

## Shared conformance suite

Every adapter runs the same parameterized tests against each declared backend version:

1. insert and retrieve one active record;
2. retry an identical upsert without duplication;
3. store two occurrences sharing one `chunk_hash`;
4. update offsets as a move without requesting an embedding;
5. tombstone a record and prove it is absent from every query path;
6. repeat the tombstone safely;
7. reject or reconcile a stale expected root;
8. interrupt a multi-record apply and resume to one consistent state;
9. verify missing, unexpected, and mismatched records;
10. compact expired tombstones while retaining active and rollback-window records;
11. isolate collections/namespaces and tenant filters;
12. reject reserved-metadata collisions and redact secrets from errors.

Backend eventual-consistency windows must be handled with bounded polling in tests, not fixed sleeps. Test fixtures must clean up only their uniquely named namespace.

## Conformance levels

- **Full:** active server-side filtering plus stale-plan protection and an atomic batch or tested staging protocol.
- **Degraded deletion:** no reliable active filter; synchronous physical deletion is required and rollback history is unavailable.
- **Experimental:** required tests are incomplete or backend/version coverage is not maintained.

Documentation for an adapter must name its level, backend and SDK versions, missing capabilities, consistency assumptions, and any operational setup required by its tests.

## Adding an adapter

Keep its optional SDK import inside the adapter/provider boundary, add an install extra only when needed, implement capability discovery, and register the shared suite. Include a small integration example that uses non-secret environment-variable names and a uniquely scoped test collection. Do not add a “supported” label until conformance evidence is present in CI.
