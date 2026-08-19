# Quick start

This walkthrough creates a small offline project, inspects the work, builds the index, retrieves a chunk, and verifies durable state. It uses no API account and sends no data over the network.

## 1. Create a project

Start in an empty directory and initialize the configuration:

```bash
mkdir steadlith-demo
cd steadlith-demo
steadlith init
```

The command writes `steadlith.toml`. The generated configuration includes Markdown under `docs/` and `README.md`, stores reusable embeddings in `.steadlith/cache.sqlite3`, and stores the index in `.steadlith/index.sqlite3`.

Create `docs/notes.md`:

```markdown
# Release notes

Steadlith assigns content-defined identities to chunks.
Unchanged chunk identities can reuse cached embeddings.

The index command publishes one SQLite snapshot after embedding succeeds.
```

## 2. Preview the index

```bash
steadlith plan
```

The plan reports the target corpus root, operation counts, cache hits, required embeddings, token estimate, and configured cost estimate. It does not write the cache or index and does not construct an embedding provider.

For automation:

```bash
steadlith plan --json
```

## 3. Build the index

```bash
steadlith index
```

The default provider computes deterministic lexical feature vectors locally. The index is published only after every required vector is available.

Run the same command again:

```bash
steadlith index
```

The second plan should contain only `keep` operations and require no new embeddings.

## 4. Query active content

```bash
steadlith query "cached embeddings"
```

The result includes a cosine score, source document, offsets, and chunk text. The default hash provider works for matching words and short phrases. It does not infer that two different words have the same meaning.

To consume results in a program:

```bash
steadlith query --json -k 3 "cached embeddings"
```

## 5. Inspect and verify state

```bash
steadlith status
steadlith verify
```

`status` shows the committed generation, corpus root, chunk counts, embedding identity, drift, and pending operations. `verify` independently checks the stored manifest and active index records.

## 6. Make a small edit

Add a paragraph to `docs/notes.md`, then preview the delta:

```bash
steadlith plan
```

Review which chunk occurrences are added, kept, moved, or deleted. Apply the edit:

```bash
steadlith index --allow-delete
```

The deletion flag is required whenever old active occurrences will become tombstones. It protects against accidental partial source scopes and overly broad exclude rules.

## Files created by the workflow

| Path | Purpose | Commit it? |
| --- | --- | --- |
| `steadlith.toml` | Project configuration and source scope | Yes |
| `.steadlith/cache.sqlite3` | Content-addressed embedding cache | Usually no |
| `.steadlith/index.sqlite3` | Active and tombstoned index records | Usually no |
| `.steadlith/index.sqlite3.manifest.json` | Diffable mirror of the committed manifest | Usually no |
| `.steadlith/index.sqlite3.migrations/` | Checksummed migration receipts | Usually no |

Back up the database and cache if they are expensive to reproduce. The cache and index contain derived information from source documents and may be sensitive.

## Next steps

- Read [Core model](core-model.md) before using positional paths.
- Review every field in [Configuration](configuration.md).
- Select a learned provider in [Embedding providers](../guides/embedding-providers.md).
- Use [Indexing](../guides/indexing.md) for deletion approvals and automation.
