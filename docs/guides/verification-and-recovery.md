# Verification and recovery

Steadlith exposes separate checks for source drift, durable index consistency, migration interruption, and stale writes.

## Status

```bash
steadlith status
steadlith status --json
```

Status reports:

- committed corpus root and generation;
- document, active chunk, and tombstone counts;
- committed model and parameters identities;
- hard-cut count and rate;
- source drift against stored filesystem metadata;
- current pending plan counts for configured sources.

Source drift means the configured files no longer match the committed snapshot. It is not itself corruption. Run `plan`, review the delta, and apply when intended.

Embedding drift means the current configuration identity differs from the committed index identity. Migrate before querying.

## Verify

```bash
steadlith verify
```

Verification checks the authoritative SQLite manifest and active records, including roots, ordered occurrence identities, model and parameter identity, offsets, token counts, metadata, stored text, vector shape, finite values, and record digests.

Exit code 2 indicates a mismatch. Stop writes, retain all state files, and capture `verify --json` output before attempting restoration.

Verification confirms internal consistency. It does not prove that source content is correct, that embeddings are semantically good, or that a cache import was authentic.

## Stale plan rejection

Each apply carries an expected generation and previous corpus root. SQLite checks both inside the write transaction. This detects:

- two writers prepared from the same state;
- same-root model migrations racing each other;
- metadata-only and move-only races;
- a later index update between planning and publication.

Prepare a fresh plan after this error. Do not retry an old in-memory `PreparedIndex`.

## Failure before index commit

If provider or cache work fails before publication, the active index generation remains unchanged. Successfully cached batches may remain and reduce work on the next run.

Run:

```bash
steadlith status
steadlith plan
```

Then retry after correcting the provider or storage failure.

## Failure after index commit

The SQLite index is authoritative. The human-readable manifest mirror is written after commit. If mirror writing fails, the command reports that the index committed and asks for verification.

Run:

```bash
steadlith verify
steadlith status
```

A later successful apply refreshes the mirror. Do not treat a stale mirror as permission to replace the database.

## Pending migration journal

If ordinary commands report a pending migration, run only:

```bash
steadlith migrate --recover
```

See [Migrations](migrations.md#recover-an-interrupted-migration). Manual journal deletion removes the information needed to decide which half of the operation completed.

## Restore from backup

Restore the config, index, cache, source revision, manifest mirror, and migration receipt directory as one set when possible.

After restoration:

```bash
steadlith verify
steadlith status
steadlith plan
steadlith query "known control query"
```

If the cache is absent but the active index verifies, querying still works because active vectors live in the index. A later edit or migration can require provider access for missing cache identities.

## Collect a useful incident report

Include:

- `steadlith --version`;
- Python version and operating system;
- command and exit code;
- full error text;
- redacted `steadlith.toml`;
- `status --json` and `verify --json` output;
- whether another process could write the database;
- storage type and free space;
- the last successful operation.

Do not attach source documents, databases, cache exports, API keys, or private migration journals to a public issue.
