# Querying

`steadlith query` embeds one query with the active index's embedding identity and ranks active SQLite records by cosine similarity.

```bash
steadlith query "how are deleted chunks handled?"
```

Limit the result count:

```bash
steadlith query -k 10 "migration rollback"
```

Use JSON in applications:

```bash
steadlith query --json -k 5 "cache identity"
```

## Preconditions

Querying is rejected when:

- the index does not exist;
- the index has no active chunks;
- query text is empty;
- the limit is not positive;
- configured model or provider parameters differ from committed index identity;
- configured dimensions differ from committed vector dimensions;
- the provider returns malformed or non-finite vectors;
- stored candidate vectors fail dimension or finite-value validation.

When configuration changed, run `steadlith plan` and use the [migration workflow](migrations.md). Do not edit the database metadata to bypass identity checks.

## Result fields

Each match contains:

| Field | Meaning |
| --- | --- |
| `score` | Cosine similarity to the query vector. |
| `chunk_hash` | Stable content identity of the chunk. |
| `text` | Canonical chunk text stored in the index. |
| `document_id` | Source path relative to the configuration directory. |
| `start_offset` | Inclusive source character offset. |
| `end_offset` | Exclusive source character offset. |
| `metadata` | Source and boundary metadata captured during indexing. |

Only active records are eligible. Tombstoned rows are excluded before scoring.

## Offline lexical retrieval

The starter configuration uses deterministic signed feature hashing over lowercase word unigrams and adjacent bigrams. It is useful for exact terms, identifiers, error messages, keywords, and short phrase overlap.

It does not understand synonyms, paraphrases, intent, or general semantic similarity. A query for `vehicle` may not retrieve a passage containing only `car`.

Use it when:

- offline behavior is required;
- keyword retrieval is sufficient;
- a deterministic local smoke test is needed;
- no model artifacts or credentials should be installed.

Do not present hash-provider results as semantic retrieval quality.

## Learned embeddings

Use the OpenAI or sentence-transformers adapter when retrieval must generalize beyond shared terms. Validate a model with questions and evidence from the target corpus before migrating.

```bash
steadlith measure retrieval --scoring lexical --json
steadlith measure retrieval --scoring hash-embedding --json
```

The bundled fixture scores are regression checks, not a substitute for an application evaluation. For a learned provider, build a private evaluation set and compare recall, ranking, latency, resource use, and cost.

## Query execution characteristics

The SQLite adapter performs an exact brute-force scan of active vectors. It keeps only the best `k` candidates in memory, but query time grows with active chunk count and vector dimension.

Measure on production-shaped data before choosing this backend for an online request path. The current query API has no metadata filter or approximate nearest-neighbor index.

## Serving from an application

The supported high-level Python function is available from `steadlith.index.service`:

```python
from steadlith.config import load_config
from steadlith.index.service import query_index

config = load_config("steadlith.toml")
matches = query_index(config, "cache identity", limit=5)

for match in matches:
    print(match.score, match.document_id, match.text)
```

This integration surface is documented for advanced use but is not one of the four frozen top-level exports. Review the [compatibility policy](../compatibility.md) before coupling application code to internal modules.

Do not share a writable SQLite connection across threads. The service opens and closes its own short-lived handle for each operation.
