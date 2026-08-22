# Architecture

## Status and intent

This document defines Steadlith's architectural boundaries. The 1.x surface is intentionally limited; documented compatibility guarantees are defined in the compatibility policy. The purity, identity, and deletion constraints below are design invariants rather than optional conventions.

## System shape

Steadlith separates deterministic decisions from effects:

```text
source text
    |
    v
normalized word stream --> chunk boundaries --> content identities
                                                  |
old manifest -------------------------------> manifest diff
                                                  |
                                                  v
                                         side-effect-free plan
                                                  |
                                    explicit apply / adapter boundary
                                      /           |            \
                               cache lookup   embedding call   vector index
```

The planner can therefore answer “what would change?” without credentials, network calls, or writes. Applying that plan is a separate operation.

## Layers and dependency direction

| Layer | Responsibility | May depend on |
| --- | --- | --- |
| `chunk` | normalization, rolling fingerprints, boundary selection, optional local snapping | standard-library pure data/functions |
| `content` | chunk hashes, manifests, Merkle roots | `chunk`, pure hashing/data functions |
| `index.plan` | manifest comparison, operations, estimates | `content`, price inputs supplied by caller |
| `store` | content-addressed embedding cache | domain types and local persistence APIs |
| `embed` | provider adapters, batching, retry/resume | provider-specific optional dependencies |
| `index.adapters` | vector-record writes, tombstones, filtering, verification | backend-specific optional dependencies |
| `index.apply` | transactional orchestration of a validated plan | cache, embedder, index adapter |
| `measure` | churn and retrieval evaluation | public chunking/planning APIs plus fixtures |
| CLI/config | user interaction, files, environment, reporting | all application-layer services |

Dependencies flow downward toward the pure core. The `chunk` and `content` packages must never import config, CLI, provider, storage, clock, filesystem, or network code.

## Core domain records

### Chunk

A chunk carries canonical text, source offsets, a token-count estimate, and boundary diagnostics. Offsets identify where content came from; they are not part of content identity. Moving identical content within a document can therefore become a metadata-only operation.

### Manifest

A document manifest is an ordered sequence of chunk occurrences plus source metadata. A corpus manifest maps stable document identifiers to document roots. Keep occurrence identity separate from content identity: the same content hash can legitimately appear several times in one document, while its embedding should still be cached once.

### Plan

A plan classifies occurrences as:

- `add`: new content occurrence; embed only on a cache miss;
- `keep`: content and relevant metadata are unchanged;
- `move`: content is unchanged but offsets or placement changed;
- `delete`: an old occurrence is no longer active.

A plan may include token and price estimates only when those inputs are known. Unknown prices must remain unknown rather than being silently treated as zero.

## Identity model

Chunk identity and embedding identity are deliberately separate:

```text
chunk_hash = H(
    identity_schema_version,
    normalizer_version,
    chunker_id,
    chunker_parameters_hash,
    canonical_chunk_text,
)

embedding_cache_key = (
    chunk_hash,
    embedding_model_id,
    embedding_parameters_hash,
)
```

An embedding model never enters `chunk_hash`. This permits model migration without re-chunking and prevents chunker changes from evicting otherwise usable embedding-cache entries.

All identity inputs require unambiguous serialization with explicit type/length boundaries. Do not hash values joined by an ad hoc delimiter. A schema-version change is a cache migration event and must be visible in a dry-run plan.

## Merkle state

Document leaves are chunk hashes in source order, including a leaf for each repeated occurrence. Internal nodes hash typed child records until one document root remains. The corpus root hashes stable document identifiers with their document roots in deterministic order.

Merkle roots serve two purposes:

1. skip subtrees whose roots match during comparison; and
2. provide a compact, verifiable identifier for an expected index state.

Canonical empty-tree and odd-node rules must be tested and versioned. A Merkle root is not a signature: authenticity still requires a trusted manifest or separate signing scheme.

## Planning and applying

Planning is referentially transparent for fixed inputs. It reads two manifest values plus explicit cost data and returns a plan. It must not probe providers, mutate caches, or reserve vector identifiers.

Applying validates that the plan's expected old root still matches current state, resolves cache hits, embeds missing content, stages vector operations, commits index changes, and finally advances durable manifest state. A crash must leave either the old committed state or a resumable staged state, never an apparently successful partial state.

The local cache commits each completed provider batch, so a later crash resumes from those commits. There remains an unavoidable acceptance-to-cache window: if a provider accepted a request and the process dies before the cache commit, a retry can be billed again. Strict no-duplicate-spend behavior requires a provider-supported idempotency key and is not claimed by the current provider interface. Backend-specific behavior belongs behind adapters and requires backend-specific tests before support is claimed.

## Deletion model

Logical deletion precedes physical deletion. Each indexed occurrence carries `valid_from` and optional `valid_to`; normal query paths select only active records. `compact` may physically remove expired tombstones later.

Active-record filtering is therefore required of any supported adapter. See the current [adapter status](adapter-conformance.md).

## Configuration boundary

TOML parsing resolves user input into immutable, validated domain parameters at the application edge. Pure functions receive those values directly. Unknown keys, impossible size relationships, and unsupported adapter/provider combinations fail as configuration errors before a plan or write begins.

Secrets are references or environment inputs consumed at provider construction time. They must never be copied into manifests, plans, cache keys, reports, or logs.

The bundled SQLite adapter stores exactly one logical index per database file. `collection` and `alias` settings are rejected because namespace isolation and staged alias swaps are not implemented. `migrate` previews configuration and index deltas by default and requires `--apply` for publication. Preview parses the proposed TOML in memory, uses read-only SQLite connections, and never constructs a provider; SQLite may maintain its normal WAL bookkeeping files, but config, index generations/rows, cache entries, and receipts do not change. Apply still rechecks the generation and old root inside the normal write transaction. It atomically replaces the TOML config after the index commit and records both a crash-recovery journal and checksummed migration receipt. A rollback is a checked forward transaction to the receipt's prior config and corpus root, so tombstone history remains intact.

## Extension points

New providers and vector backends are optional adapters. Importing `steadlith` must not import their SDKs or require network access. Provider/model identity must be explicit and stable; backend adapters must expose capabilities and pass conformance tests.

Any alternative chunker used for benchmarking must be identified explicitly. Changes to the default CDC algorithm require locality, determinism, churn, and retrieval evidence plus a new identity version.
