# Operations

The SQLite backend is a single-host reference deployment. This guide covers the checks needed before placing it in a durable application workflow.

## Deployment boundary

Steadlith provides:

- one logical index per SQLite database file;
- atomic snapshot publication;
- active-only exact vector search;
- stale-writer rejection;
- tombstones and explicit compaction;
- content-addressed embedding reuse;
- consistency verification.

It does not provide:

- a network query service;
- access control or tenant namespaces;
- remote vector database adapters;
- replication, leader election, or automatic failover;
- online backups or scheduled jobs;
- approximate nearest-neighbor indexes;
- provider request tracing or distributed telemetry.

Build those concerns in the application or platform around Steadlith.

## Filesystem layout

Keep config and managed state on a local filesystem with reliable file locking and atomic replace semantics:

```text
project/
  steadlith.toml
  sources/
  .steadlith/
    cache.sqlite3
    index.sqlite3
    index.sqlite3.manifest.json
    index.sqlite3.migrations/
```

Do not place a writable SQLite database on a network filesystem without validating locking and durability behavior for that exact environment.

## Process model

Readers can query while a writer prepares embeddings. Publication uses a short SQLite transaction. Multiple planned writers are safe from silent overwrite because generation checks reject stale state, but applications should still serialize index updates to reduce wasted provider work.

Recommended roles:

- one scheduled or operator-controlled writer per logical index;
- application readers that open state read-only through the service layer;
- no direct SQL mutation;
- no long-lived connection shared across threads or processes.

## Backup and restore

Back up:

1. `steadlith.toml`;
2. source revision or source snapshot;
3. index database;
4. embedding cache;
5. manifest mirror;
6. migration receipt directory;
7. any pending migration journal;
8. the Steadlith package version.

Use SQLite's backup API or stop writers before copying database files. Test restore regularly with `verify`, `status`, a no-op `plan`, and control queries.

The source corpus remains the primary data. Index and cache are derived state, but provider cost, offline model availability, and audit needs can make them operationally important.

## Permissions and secrets

- Restrict config and state directories to the application account.
- Protect source text, vectors, metadata, and cache exports according to the source data classification.
- Set `OPENAI_API_KEY` in the runtime secret store, not TOML.
- Do not allow untrusted repositories to select arbitrary secrets or provider endpoints.
- Import cache artifacts only after authenticating their source.
- Remember that SQLite files are not application-level encrypted by Steadlith.

## Capacity planning

Measure these on representative data:

- source byte and chunk counts;
- mean and high-percentile chunks per document;
- vector dimensions and encoded bytes;
- cache hit rate after common edits;
- plan and chunking time;
- provider latency and throughput;
- apply transaction duration;
- exact-query latency at expected active chunk count;
- database and cache growth under tombstone retention;
- backup and restore time.

The exact SQLite query scans active vectors, so active chunk count times vector dimensions is the central query cost driver.

## Routine checks

Before apply:

```bash
steadlith plan --json
```

After apply:

```bash
steadlith status --json
steadlith verify --json
```

Periodically:

```bash
steadlith cache stats --json
steadlith compact --dry-run --json
steadlith measure churn --json
steadlith measure retrieval --scoring hash-embedding --json
```

Run application-specific retrieval evaluation separately. The bundled fixtures protect Steadlith behavior, not your answer quality.

## Compaction policy

Tombstones make deletions immediately unreachable without destroying historical rows. Decide a retention window that covers rollback and incident investigation needs.

Preview a cutoff:

```bash
steadlith compact --dry-run --before 2026-08-01T00:00:00Z
```

Apply after backup and review:

```bash
steadlith compact --before 2026-08-01T00:00:00Z
```

Compaction is irreversible for those index rows. It does not prune the embedding cache.

## Upgrade procedure

1. Read the changelog and compatibility policy.
2. Back up config, state, and source revision.
3. Upgrade Steadlith in a staging copy.
4. Run `verify`, `status`, and `plan` without applying.
5. Run control retrieval questions.
6. Upgrade the production environment.
7. Repeat verification before accepting writes.

Persisted schema versions fail closed when unsupported. Do not work around a version error by changing rows or manifests manually.
