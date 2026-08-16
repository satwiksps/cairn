<p align="center">
  <img src="https://raw.githubusercontent.com/satwiksps/cairn/main/assets/cairn-banner.svg" alt="Cairn" width="100%">
</p>

# Cairn

[![CI](https://github.com/satwiksps/cairn/actions/workflows/ci.yml/badge.svg)](https://github.com/satwiksps/cairn/actions/workflows/ci.yml)
[![Codecov](https://codecov.io/gh/satwiksps/cairn/graph/badge.svg)](https://codecov.io/gh/satwiksps/cairn)
[![PyPI](https://img.shields.io/pypi/v/cairn-rag)](https://pypi.org/project/cairn-rag/)
[![Python](https://img.shields.io/pypi/pyversions/cairn-rag)](https://pypi.org/project/cairn-rag/)
[![License](https://img.shields.io/github/license/satwiksps/cairn)](LICENSE)

> Cairn reuses unchanged RAG chunks with content-defined identities, cache-aware planning, and transactional indexing.

Cairn is a Python toolkit for stable, incremental retrieval-augmented generation (RAG) indexing. It combines content-defined chunking, content-addressed identities, and a dry-run planner so a small edit can be represented as a small set of index operations.

The distribution, Python module, and command are `cairn-rag`, `cairn_rag`, and `cairn-rag`. The distinct public namespace avoids collisions with the unrelated [existing `cairn` project on PyPI](https://pypi.org/project/cairn/), which already owns both the `cairn` module and command.

The v1 chunk-identity schema is compatibility-stable and protected by golden-vector tests. Built-in five-corpus benchmarks publish churn and retrieval baselines for every bundled chunking strategy. The default offline provider performs lexical retrieval; select a learned provider when queries require semantic similarity.

The workspace's `cairn-project-spec.md` is historical design input and is excluded from release artifacts. Maintained documentation, tests, and measured results define the supported behavior.

## Why Cairn exists

Hashing chunks only avoids work when chunk boundaries stay stable. Offset-based chunkers can shift every downstream boundary after an insertion near the start of a document, which changes hashes even where the underlying text did not change.

Cairn's default `cdc-rabin` strategy places candidate boundaries from a rolling fingerprint over normalized words. Boundaries far from a local edit should therefore remain stable. A manifest diff then classifies each chunk as `add`, `keep`, `move`, or `delete`. When embedding identity is unchanged, only uncached `add` content needs a new embedding; a model or embedding-parameter migration may re-embed otherwise unchanged occurrences.

Cairn is deliberately a library and planner, not a RAG framework. The intended integration point is below orchestration libraries and above embedding/vector providers.

## Supported scope

The reference path is implemented end to end:

- deterministic normalized-word chunking with Rabin content-defined boundaries;
- content-addressed chunks and embedding-cache keys;
- manifests, Merkle roots, and explicit change plans;
- a local CLI, SQLite index, and SQLite embedding cache;
- migration with preview, recovery, and rollback;
- versioned churn and retrieval regressions across five built-in corpora;
- cross-platform determinism, adapter, crash-recovery, deletion, and query tests.

Sentence/paragraph snapping remains opt-in because it needs project-specific legal review. The default unsnapped strategy does not depend on it.

## Installation

Cairn requires Python 3.10 or newer.

Install the latest published release:

```bash
python -m pip install cairn-rag
```

For an isolated command-line installation, use `pipx`:

```bash
pipx install cairn-rag
```

For development, install from a source checkout:

```bash
git clone https://github.com/satwiksps/cairn.git
cd cairn
python -m pip install -e ".[dev]"
```

Releases are built and published by the tag-triggered workflow described in the [release checklist](https://github.com/satwiksps/cairn/blob/main/docs/release-checklist.md).

Provider SDKs are optional and do not load with the core package. From a source checkout:

```bash
python -m pip install -e ".[openai]"
python -m pip install -e ".[sentence-transformers]"
```

## Quick start

Create a local configuration and inspect a plan before applying it:

```bash
cairn-rag init
cairn-rag plan
cairn-rag index
cairn-rag status
cairn-rag query "your question"
cairn-rag verify
```

With no explicit paths, `cairn-rag plan` and `index` use the committed `[sources]` globs. `plan` is the safe starting point: it reports proposed adds, keeps, moves, and deletes without writing index state.

> [!CAUTION]
> Paths passed to `plan` or `index` are the complete desired corpus for that run. Previously indexed documents omitted from that scope are planned as deletions. Prefer the committed `[sources]` globs and inspect `cairn-rag plan` before applying changes. `index` requires `--allow-delete` for a deleting plan and also requires `--allow-empty` before emptying a previously populated corpus.

The generated starter configuration uses deterministic unigram/bigram feature hashing. It works offline for exact-term and keyword retrieval but does not infer synonyms or semantic similarity. Use the OpenAI or sentence-transformers provider when semantic matching is required.

See the [CLI reference](https://github.com/satwiksps/cairn/blob/main/docs/cli.md) before automating a workflow; in particular, positional paths describe a complete desired corpus rather than additions to the existing index.

Programmatic use keeps chunking separate from provider and backend concerns:

```python
from cairn_rag import CDCChunker
from cairn_rag.config import load_config

chunker = CDCChunker.from_config(load_config("cairn.toml"))
chunks = chunker.split("A document that changes a little at a time.")

for chunk in chunks:
    print(chunk.text)
```

`load_config` performs file I/O at the application edge; the chunker receives the parsed object and remains independent of files, providers, and backends.

The documented top-level API and JSON outputs follow the [compatibility policy](https://github.com/satwiksps/cairn/blob/main/docs/compatibility.md). Chunk identity `cairn-chunk-identity-v1` will not change silently across package releases.

## Configuration

The complete sample is in [`examples/cairn.toml`](https://github.com/satwiksps/cairn/blob/main/examples/cairn.toml). The default strategy is unsnapped Rabin CDC:

```toml
[chunker]
strategy = "cdc-rabin"
window_words = 48
min_tokens = 180
max_tokens = 640
snap_window_words = 24
```

Snapping is enabled only by selecting `strategy = "cdc-rabin+snap"`; it is never enabled by the plain default strategy.

Changing normalization or chunking parameters changes chunk identity. Always run `cairn-rag plan` before applying a configuration change.

## Design constraints

- `chunk` and `content` stay deterministic and free of I/O, network access, and configuration lookups.
- The embedding model is not part of the chunk hash. Embedding cache keys add model and model-parameter identities separately.
- Snapping may inspect only a bounded local window and is never enabled implicitly.
- Deletes become tombstones before compaction so removed content cannot silently remain active.
- Benchmark reporting must publish churn and retrieval-quality results together.

## Documentation

- [CLI reference](https://github.com/satwiksps/cairn/blob/main/docs/cli.md): commands, output modes, corpus scope, exit codes, and destructive operations.
- [Backends and providers](https://github.com/satwiksps/cairn/blob/main/docs/backends-and-providers.md): the implemented support matrix and production caveats.
- [Architecture](https://github.com/satwiksps/cairn/blob/main/docs/architecture.md): boundaries, identities, manifests, planning, and deletion.
- [Chunking algorithm](https://github.com/satwiksps/cairn/blob/main/docs/algorithm.md): implemented Rabin/TTTD behavior and locality acceptance targets.
- [Benchmarks](https://github.com/satwiksps/cairn/blob/main/docs/benchmarks.md): reproducible five-corpus churn and retrieval results.
- [Compatibility](https://github.com/satwiksps/cairn/blob/main/docs/compatibility.md): stable identities, public surfaces, and migration rules.
- [Known limitations](https://github.com/satwiksps/cairn/blob/main/docs/limitations.md): current correctness, quality, legal, and operational constraints.
- [Adapter conformance](https://github.com/satwiksps/cairn/blob/main/docs/adapter-conformance.md): requirements for additional index backends.
- [Release checklist](https://github.com/satwiksps/cairn/blob/main/docs/release-checklist.md): work intentionally required before public publishing.
- [Landing website](https://github.com/satwiksps/cairn/blob/main/website/README.md): local development and Vercel deployment instructions.

## When Cairn is a fit

Cairn is aimed at large documents or corpora where edits are small relative to the indexed content. It may offer little advantage for short documents that are normally replaced wholesale, and content-defined boundaries may retrieve differently from semantically selected boundaries. Measure both churn and retrieval quality on your own corpus.

## Contributing and security

Contributions are welcome. Start with [`CONTRIBUTING.md`](https://github.com/satwiksps/cairn/blob/main/CONTRIBUTING.md), follow the [`CODE_OF_CONDUCT.md`](https://github.com/satwiksps/cairn/blob/main/CODE_OF_CONDUCT.md), and add tests for behavior changes. Report vulnerabilities privately as described in [`SECURITY.md`](https://github.com/satwiksps/cairn/blob/main/SECURITY.md).

## License

Cairn is available under the [Apache License 2.0](https://github.com/satwiksps/cairn/blob/main/LICENSE).
