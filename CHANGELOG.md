# Changelog

All notable changes to Cairn are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases use
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-08-16

### Added

- A compatibility policy that freezes `cairn-chunk-identity-v1`, backed by golden-vector tests.
- Published five-corpus churn and retrieval tables with CI-enforced regression thresholds.
- Direct PyPI installation and package links throughout the website and documentation.

### Changed

- The offline hash provider is documented and tested as lexical unigram/bigram retrieval rather than dismissed as test-only infrastructure.
- Project status now reflects the supported local SQLite workflow while retaining explicit semantic, TTTD-locality, snapping, and remote-provider boundaries.
- Unknown chunk-identity schema versions fail closed instead of being accepted as arbitrary hash inputs.

### Fixed

- Release automation now supplies repository context when creating a GitHub Release from an artifact-only job.

## [0.1.0] - 2026-08-16

### Added

- Deterministic fixed, recursive, semantic, Rabin CDC, and bounded-snap chunking strategies.
- Content-addressed chunk identities, manifests, Merkle roots, and add/keep/move/delete plans.
- SQLite embedding cache and transactional SQLite index with tombstones, verification, and compaction.
- Offline hash embeddings plus optional OpenAI and sentence-transformers providers.
- CLI workflows for initialization, planning, indexing, querying, migration, measurement, and cache management.
- Migration preview, apply, recovery, and rollback with durable receipts and stale-state protection.
- Reproducible churn and retrieval measurement fixtures.
- Next.js project website and automated Python/package/website release workflows.

### Security

- Source discovery confines inputs to the configured project root and excludes Cairn-managed state.
- Destructive index operations require explicit deletion and empty-corpus consent.
- Network providers and unsigned cache imports require explicit trust flags.

### Known limitations

- Package APIs were initially published without a compatibility guarantee.
- The current stateful TTTD fallback does not provide a strict fixed-margin locality guarantee.
- The bundled hash embedder is deterministic test infrastructure, not a production retrieval model.
- Post-anchor structural snapping is experimental and requires project-specific legal review before use.

[Unreleased]: https://github.com/satwiksps/cairn/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/satwiksps/cairn/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/satwiksps/cairn/releases/tag/v0.1.0
