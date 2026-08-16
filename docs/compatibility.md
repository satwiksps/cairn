# Compatibility policy

Cairn separates content identity from package version so existing indexes remain explainable across upgrades.

## Stable chunk identity

`cairn-chunk-identity-v1` is frozen. Given identical canonical text, normalization version, chunker name, and chunker-parameter hash, supported Cairn releases produce the same SHA-256 chunk hash.

The v1 contract includes:

- length-delimited hash serialization;
- `cairn-normalizer-v1` whitespace and paragraph normalization;
- the tokenizer identity;
- rolling-hash and boundary-rule identities;
- minimum, maximum, mask, window, and snapping parameters;
- canonical chunk text.

The embedding provider and model are intentionally outside the chunk hash. They remain part of the embedding-cache key.

Golden-vector tests pin the default parameter hash and a representative chunk hash. A future incompatible algorithm must use a new normalizer, boundary-rule, parameter, or identity version. It must not reinterpret v1 data.

## Configuration and migrations

Changing an identity-bearing setting creates new chunk identities. `cairn-rag plan` shows the resulting work, and `cairn-rag migrate --dry-run` prices a chunker or embedding change before it is applied.

Manifests and SQLite state carry explicit schema versions. Unsupported versions fail closed rather than being read as a newer format.

## CLI and Python surfaces

The documented top-level Python exports are `CDCChunker`, `CDCParams`, `Cache`, and `Chunk`. These exports are the supported library surface. Internal modules may change.

Documented CLI commands, exit codes, and existing JSON fields remain compatible within a minor release. Compatible releases may add JSON fields; consumers must ignore fields they do not recognize. A removal or meaning change requires release notes and a versioned migration path where persisted state is affected.

## Scope of the guarantee

Compatibility does not mean every configuration produces the same chunks. Parameters are identity inputs precisely so intentional changes remain detectable. It also does not turn the stateful TTTD rule into a formal fixed-distance locality guarantee; locality evidence and limits are documented separately.
