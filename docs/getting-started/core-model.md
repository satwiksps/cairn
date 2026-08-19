# Core model

Steadlith treats an index as a complete, versioned snapshot of a corpus. Five ideas explain most behavior.

## Source scope is complete

The configured `[sources]` globs, or positional paths passed to `plan` and `index`, describe the entire desired corpus for that run. Positional paths are not additions to an existing index.

If `guide.md` and `manual.md` are active, this command proposes deletion of `manual.md`:

```bash
steadlith index guide.md
```

The command refuses to apply that deletion without `--allow-delete`.

Use no positional paths for repeatable project automation:

```bash
steadlith plan
steadlith index
```

## A chunk has content identity

A chunk hash covers the normalized chunk text and every algorithm setting that affects chunk boundaries. Offsets, source paths, and embedding models do not participate in the chunk hash.

The same chunk text under the same v1 identity settings has the same hash across documents and runs. This lets the embedding cache reuse a vector when the same content appears again.

## Embeddings have a separate identity

The cache key is:

```text
(chunk_hash, embedding_model_id, embedding_parameters_hash)
```

Changing an embedding model does not alter chunk hashes, but it creates a different cache identity and can require new vectors for every active chunk.

## A plan separates reading from writing

`steadlith plan` reads sources, builds the target manifest, reads current state, and checks cache keys. It does not call the provider and does not mutate state.

`steadlith index` prepares the same plan, checks approval gates, resolves cached vectors, embeds misses, and commits one new index generation.

If another writer changes the index after a plan is prepared, the generation and root checks reject the stale apply.

## Deletion is logical before it is physical

Removed active records receive a `valid_to` timestamp and stop appearing in queries immediately. They remain as tombstones until `compact` physically removes them.

This split supports inspection and migration rollback. It also means disk use can grow after repeated changes until the operator compacts old rows.

## State has a verifiable root

Ordered chunk hashes form a document Merkle root. Ordered document roots form the corpus root. The root identifies the committed content state, while the generation distinguishes transactions that can retain the same content root, such as model migrations.

Use both concepts when debugging:

- Root changed: content identity or document order changed.
- Generation changed with the same root: durable state changed without changing chunk content, commonly an embedding migration.
- Source drift with no generation change: files differ from the last committed manifest.

Read [Manifests and Merkle roots](../concepts/manifests-and-merkle.md) and [Planning and transactions](../concepts/planning-and-transactions.md) for the full model.
