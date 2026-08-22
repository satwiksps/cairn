# Backends and embedding providers

Steadlith has one supported local index backend and three embedding-provider adapters. "Included" means the adapter exists in this repository; optional providers still require validation against the selected live service or model.

Install optional providers with `pip install "steadlith[openai]"` or `pip install "steadlith[sentence-transformers]"`.

## Index backend support

| Backend | Install | Current status | Important boundaries |
| --- | --- | --- | --- |
| SQLite | Core package | Supported local backend | One logical index per database file; local transactional snapshot apply, active-record filtering, tombstones, brute-force vector queries, verification, and compaction. No collection namespaces, alias swaps, remote service, replication, or high-availability claim. |
| Other vector databases | N/A | Not implemented | No reusable conformance harness or additional backend is present. |

Use a distinct `[index].database` path for each logical index. `collection` and `alias` configuration keys are rejected rather than ignored. SQLite is useful for development, local evaluation, and the end-to-end reference path; capacity, concurrency, backup, and availability must be evaluated before any production use.

See [adapter status](adapter-conformance.md) for the behavior covered by the SQLite tests.

## Embedding-provider support

| Provider value | Install | Network/account | Current status and constraints |
| --- | --- | --- | --- |
| `hash` | Core package | Neither | Deterministic unigram/bigram feature hashing for offline lexical retrieval. Suitable for exact-term and keyword matching; it does not infer semantic similarity or synonyms. |
| `openai` | `pip install "steadlith[openai]"` | Official API and key | Optional adapter. The configuration accepts only the official endpoint and `OPENAI_API_KEY`; custom endpoints and credential-variable names are rejected. It passes configured model/dimensions to the embeddings API. Model availability, dimension support, and quotas remain operator responsibilities. |
| `sentence-transformers` | `pip install "steadlith[sentence-transformers]"` | No inference API required; model loading may download files | Optional local adapter. The configured dimensions must exactly match the loaded model. Hardware capacity, model artifacts, licenses, trust settings, and reproducibility remain operator responsibilities. |

Optional SDKs are imported only when their provider is selected. Importing `steadlith` does not require provider credentials or network access.

## Configuration examples

OpenAI:

```toml
[embedding]
provider = "openai"
model = "YOUR_MODEL_ID"
dimensions = 1536
batch_size = 64
api_key_env = "OPENAI_API_KEY"
```

Sentence Transformers:

```toml
[embedding]
provider = "sentence-transformers"
model = "YOUR_MODEL_ID"
dimensions = 384
batch_size = 64
```

Placeholders are intentional: Steadlith does not select a current model, dimensions, endpoint, or price on the operator's behalf. Omit `price_per_million_tokens` when it is unknown; otherwise set it from a current, verified source.

Running `index` with either optional provider requires the invocation-level `--allow-network` confirmation. OpenAI sends chunk text to its API; sentence-transformers performs local inference but may download model artifacts while loading.

## Pricing and billing caveats

- `price_per_million_tokens` and `measure churn --price` are caller-supplied reporting inputs. Steadlith does not fetch, date, or verify provider prices.
- Steadlith's deterministic token estimate may differ from a provider's tokenizer and billing units. Treat the plan as an estimate, then validate it against the selected provider's current documentation and limits.
- Successfully returned batches are written to the cache before index publication. A crash after a provider accepts a request but before its cache commit can still cause the retry to be billed twice. The current interface has no provider idempotency key and makes no strict no-duplicate-spend guarantee.
- A model, dimension, endpoint, or other identity change creates a distinct cache identity. Run `plan` and a retrieval evaluation before applying it.

## Production and data-handling caveats

- A remote provider receives chunk text. Confirm data residency, privacy, retention, and acceptable-use requirements before sending a corpus.
- The local SQLite index stores chunk text, metadata, and vectors; the cache stores vectors and identity metadata. Neither file is application-level encrypted by Steadlith. Protect files with appropriate host access controls, encryption, backup, and retention policies.
- Embeddings may be sensitive and their redistribution may be restricted by source-data licenses, model licenses, privacy duties, or provider terms.
- Retries use bounded exponential backoff, but the adapters do not currently expose rate-limit coordination, request tracing, idempotency, or production telemetry.
- The optional provider adapters are not exercised against live services in default CI. Pin and test SDK/model/backend versions in the deployment environment.

For broader project caveats, read [known limitations](limitations.md).
