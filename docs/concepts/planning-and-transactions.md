# Planning and transactions

Steadlith divides an index update into a read-only computation and a checked publication.

## Preparation

`prepare_index` performs:

1. configuration validation;
2. deterministic source discovery;
3. source read with mutation detection;
4. chunking and target manifest construction;
5. read-only current index status and manifest load;
6. embedding identity calculation;
7. document diff;
8. read-only cache presence checks;
9. embedding and cost estimation.

It returns a `PreparedIndex` containing target documents, plan, old and target manifests, model identity, parameter identity, and expected generation.

No provider is constructed. No cache, database, manifest mirror, config, journal, or receipt is written.

## Diff classification

The planner compares occurrences within documents and identifies adds, keeps, moves, and deletes. Same-hash content at changed offsets can move without embedding work. Multiple duplicate hashes are matched deterministically rather than treated as one indistinguishable occurrence.

The plan separately computes:

- unique embeddings required;
- cache hits;
- estimated tokens;
- configured cost estimate;
- a naive re-embed comparison;
- whether an apply is required.

## Cache resolution

During apply, active vectors with the same embedding identity are reused first. Remaining unique chunk hashes are checked in the cache. Only misses are sent to the provider.

Successful provider batches are written to the cache before the index transaction. This makes a retry resume from completed batches, but no local transaction can guarantee provider-side billing idempotency.

## Publication transaction

SQLite starts a write transaction and validates:

- expected generation;
- expected old corpus root;
- schema version;
- record and vector constraints;
- current embedding identity where required.

It then writes target active rows and documents, tombstones superseded active rows, stores the target manifest and identity, and increments generation. Readers see either the earlier committed generation or the new one.

## Visibility and failures

| Failure point | Active index result |
| --- | --- |
| Source read or chunking | Unchanged |
| Cache lookup | Unchanged |
| Provider call | Unchanged |
| Cache write after a provider batch | Unchanged |
| SQLite transaction before commit | Rolled back |
| Manifest mirror after SQLite commit | New generation is active; command reports mirror failure |

This contract prevents a partially embedded target from becoming query-visible.

## Concurrency

Two writers can prepare from one generation. The first successful transaction increments generation. The second fails its transactional generation check even when both target corpus roots are equal.

Applications should still serialize writers. Stale rejection protects correctness, but a losing writer may already have spent time or provider cost on vectors that only become cache entries.

## No-op behavior

When the plan requires no apply, `apply_prepared` returns current counts without incrementing generation. Routine repeated indexing of an unchanged corpus is therefore stable.

## Public and advanced surfaces

The CLI is the supported operational interface. `prepare_index` and `apply_prepared` are documented advanced functions in `steadlith.index.service`; they are not frozen top-level exports. If an application stores a `PreparedIndex`, it must apply it promptly and handle stale-state failure by preparing again.
