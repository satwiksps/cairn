# JSON output

Commands that accept `--json` emit one JSON object to standard output. Human formatting and ANSI styling are disabled. User-controlled non-ASCII text remains valid JSON on legacy Windows consoles through ASCII escaping when needed.

## Compatibility rules

- Existing documented fields remain compatible within a minor release.
- Compatible releases may add fields.
- Consumers must ignore fields they do not recognize.
- Enum values and field meaning changes require release notes.
- Success is determined by process exit code 0, not by the presence of a particular field.
- Expected typed errors also use a JSON object when `--json` is present.

## Error object

```json
{
  "error": "Configuration does not exist: steadlith.toml",
  "error_type": "ConfigError",
  "exit_code": 4
}
```

Argument parsing errors are produced by `argparse` before command handling and use its normal stderr format.

## Plan

```json
{
  "old_root": null,
  "new_root": "hexadecimal-root",
  "changed": true,
  "requires_apply": true,
  "old_chunks": 0,
  "new_chunks": 3,
  "counts": {
    "add": 3,
    "keep": 0,
    "move": 0,
    "delete": 0
  },
  "cost": {
    "cache_hits": 0,
    "chunks_to_embed": 3,
    "tokens_to_embed": 910,
    "estimated_cost": 0.0,
    "naive_chunks_to_embed": 3,
    "naive_tokens_to_embed": 910,
    "naive_estimated_cost": 0.0,
    "avoided_embeddings": 0
  },
  "operations": []
}
```

Each operation contains `kind`, `document_id`, `chunk_hash`, `old_position`, `new_position`, `old_offsets`, and `new_offsets`. Missing sides use `null`.

## Index apply

```json
{
  "plan": {
    "old_root": null,
    "new_root": "hexadecimal-root",
    "changed": true,
    "requires_apply": true,
    "old_chunks": 0,
    "new_chunks": 3,
    "counts": {},
    "cost": {}
  },
  "active_chunks": 3,
  "tombstoned_chunks": 0,
  "cache_hits": 0,
  "embedded_chunks": 3,
  "embedded_tokens": 910
}
```

The nested apply plan omits the potentially large `operations` array.

## Status

Fields are:

```text
corpus_root, generation, documents, active_chunks, tombstoned_chunks,
hard_cuts, total_boundaries, model_id, params_hash, hard_cut_rate,
index_drift, source_drift, embedding_drift, pending_operations,
pending_embeddings
```

`pending_operations` contains all four operation keys even when their values are zero.

## Query

```json
{
  "query": "cache identity",
  "count": 1,
  "matches": [
    {
      "score": 0.75,
      "chunk_hash": "hexadecimal-hash",
      "text": "Canonical chunk text",
      "document_id": "docs/guide.md",
      "start_offset": 0,
      "end_offset": 20,
      "metadata": {}
    }
  ]
}
```

Scores are floating-point cosine similarity values. Do not compare them across different embedding identities.

## Verify

```json
{"valid": true, "problems": []}
```

A false result exits with code 2 and lists human-readable consistency problems.

## Compact

Dry run:

```json
{"eligible": 12}
```

Apply:

```json
{"removed": 12}
```

## Cache commands

Stats:

```json
{"entries": 10, "chunks": 8, "models": 2, "bytes": 10240}
```

Prune:

```json
{"removed": 4}
```

Export:

```json
{"exported": 10, "destination": "/absolute/path/cache.jsonl"}
```

Import:

```json
{"imported": 10, "source": "cache.jsonl"}
```

## Init and adopt

`init` returns `created`, `backend`, and `next`.

`adopt` returns `created`, `source`, `configured_state_paths_preserved`, `state_moved`, and `embeddings_created`.

## Migrations

A preview contains plan summary fields plus:

```text
kind, rollback_of, configuration_changes, expected_generation,
target_generation, source_scope_overridden
```

An apply wraps that preview under `migration` and returns a `result` containing `migration_id`, `receipt`, and nested `applied` apply statistics.

Recovery returns `outcome`, `migration_id`, and `receipt`. Outcome is `committed`, `aborted`, or `none`.

## Measurement output

Churn and retrieval commands emit full per-case data plus summary rows and a fixture notice. Their schema is intended for benchmark analysis rather than the operational index API. Pin the Steadlith version when storing long-lived benchmark datasets.
