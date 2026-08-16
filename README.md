# Cairn

> Cairn reuses unchanged RAG chunks with content-defined identities, cache-aware planning, and transactional indexing.

Cairn is an early-stage Python toolkit for stable, incremental retrieval-augmented generation (RAG) indexing. It combines content-defined chunking, content-addressed identities, and a dry-run planner so a small edit can be represented as a small set of index operations.

The distribution, Python module, and command are `cairn-rag`, `cairn_rag`, and `cairn-rag`. The distinct public namespace avoids collisions with the unrelated [existing `cairn` project on PyPI](https://pypi.org/project/cairn/), which already owns both the `cairn` module and command.

> [!IMPORTANT]
> Cairn is alpha software. Its chunk-identity schema is not frozen, retrieval quality has not yet been established, and the benchmark results described in the project specification have not yet been reproduced. The current TTTD boundary selector also does not satisfy the draft's proposed fixed-margin locality guarantee in all cases. Do not base production cost or quality decisions on projected results.

The workspace's `cairn-project-spec.md` is preserved as historical design input and excluded from release artifacts. Where it conflicts with the implemented tests and maintained documentation—notably on strict TTTD locality—the latter describe the current alpha behavior.

## Why Cairn exists

Hashing chunks only avoids work when chunk boundaries stay stable. Offset-based chunkers can shift every downstream boundary after an insertion near the start of a document, which changes hashes even where the underlying text did not change.

Cairn's default `cdc-rabin` strategy places candidate boundaries from a rolling fingerprint over normalized words. Boundaries far from a local edit should therefore remain stable. A manifest diff then classifies each chunk as `add`, `keep`, `move`, or `delete`. When embedding identity is unchanged, only uncached `add` content needs a new embedding; a model or embedding-parameter migration may re-embed otherwise unchanged occurrences.

Cairn is deliberately a library and planner, not a RAG framework. The intended integration point is below orchestration libraries and above embedding/vector providers.

## Status

The current alpha is focused on proving the mechanism:

- deterministic normalized-word chunking with Rabin content-defined boundaries;
- content-addressed chunks and embedding-cache keys;
- manifests, Merkle roots, and explicit change plans;
- a local CLI, SQLite index, and SQLite embedding cache;
- empirical boundary-stability checks, randomized chunking regressions, and cross-run determinism tests.

Sentence/paragraph boundary snapping is experimental and opt-in. It needs both empirical validation and project-specific patent review before broader use.

## Installation

Cairn requires Python 3.10 or newer.

Until the first public release is published, install Cairn from a source checkout:

```bash
python -m pip install -e .
```

For contributor tooling, use the development extra instead:

```bash
python -m pip install -e ".[dev]"
```

After the first public release, the distribution install will be:

```bash
python -m pip install cairn-rag
```

Publishing remains deliberately gated until an owner reserves the PyPI namespace and supplies a private security contact; see the [release checklist](https://github.com/satwiksps/cairn/blob/main/docs/release-checklist.md).

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

The generated starter configuration uses a deterministic hash embedder so the workflow can run offline. That embedder is test/demo infrastructure and is **not suitable for production retrieval or retrieval-quality evaluation**.

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

The exact public API remains subject to change before 1.0.

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
