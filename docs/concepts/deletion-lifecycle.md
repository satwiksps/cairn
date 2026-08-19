# Deletion lifecycle

Steadlith separates logical deletion from physical removal.

## Planning a deletion

A previously active document or occurrence is deleted when it is absent from the complete desired corpus. Common causes include:

- source file removal;
- an include-glob change;
- a new exclude pattern;
- a positional scope that omits earlier sources;
- chunk-boundary changes;
- embedding identity migration.

The planner shows deletes before mutation. `index` refuses any plan containing them unless `--allow-delete` is present.

Making a non-empty corpus completely empty requires both `--allow-delete` and `--allow-empty`.

## Tombstoning

During transactional publication, superseded active rows receive a `valid_to` timestamp. Queries select active rows only, so deletion is effective immediately when the transaction commits.

Tombstones retain:

- occurrence and chunk identity;
- document and position;
- stored text and metadata;
- vector;
- validity interval;
- generation history needed for inspection and migration behavior.

The document table and active manifest describe only the current target snapshot.

## Restoring content

If deleted content returns, its chunk hash may match an old row and its vector can be reused from the cache. The restored occurrence receives a new generation-scoped instance ID. Steadlith does not reactivate or rewrite the tombstoned lifecycle.

This keeps historical validity intervals coherent.

## Compaction

`compact` physically removes tombstoned vector rows at or before a UTC cutoff.

Preview:

```bash
steadlith compact --dry-run --before 2026-08-01T00:00:00Z
```

Apply:

```bash
steadlith compact --before 2026-08-01T00:00:00Z
```

Without `--before`, the current time is used. Explicit timestamps must be ISO 8601 with a timezone.

## Retention decision

Retain tombstones long enough for:

- immediate migration rollback;
- incident investigation;
- deletion correctness audits;
- restoration testing;
- operational backup windows.

Compaction is irreversible for the removed index rows. It does not delete embedding cache entries or source files.

## Security boundary

Logical deletion removes content from Steadlith queries, not from every copy. Text or vectors can remain in:

- tombstoned rows until compaction;
- embedding cache entries;
- backups and cache exports;
- logs or application responses;
- remote provider systems subject to their retention policy.

Define deletion procedures across all stores when the corpus has regulatory or contractual erasure requirements.
