# Compatibility policy

Steadlith separates content identity from package version so existing indexes remain explainable across upgrades.

## Stable chunk identity

The v1 chunk identity is frozen. Given identical canonical text, normalization version, chunker name, and chunker-parameter hash, supported releases produce the same SHA-256 chunk hash.

The v1 contract includes:

- length-delimited hash serialization;
- versioned whitespace and paragraph normalization;
- the tokenizer identity;
- rolling-hash and boundary-rule identities;
- minimum, maximum, mask, window, and snapping parameters;
- canonical chunk text.

The embedding provider and model are intentionally outside the chunk hash. They remain part of the embedding-cache key.

Golden-vector tests pin the default parameter hash and a representative chunk hash. A future incompatible algorithm must use a new normalizer, boundary-rule, parameter, or identity version. It must not reinterpret v1 data.

Steadlith 1.0 keeps the v1 chunk, Merkle, record, and hash wire domains from Cairn 0.2 byte-for-byte. Some stored identifiers therefore retain the former name. These values are isolated as immutable compatibility data. They are not package, module, command, configuration-file, or state-directory names. Renaming them would change hashes and invalidate existing indexes and cached embeddings.

## Configuration and migrations

Changing an identity-bearing setting creates new chunk identities. `steadlith plan` shows the resulting work, and `steadlith migrate --dry-run` prices a chunker or embedding change before it is applied.

To adopt a 0.2 project without recomputing its state, run:

```bash
steadlith adopt --from-config cairn.toml --config steadlith.toml
```

The command validates the old configuration and writes a normalized Steadlith configuration. It preserves existing cache and index paths and the configured model identity. It refuses an output file that already exists, paths outside the project, and adoption while a migration journal is pending. It never runs automatically.

Manifests and SQLite state carry explicit schema versions. Unsupported versions fail closed rather than being read as a newer format.

## CLI and Python surfaces

The documented top-level Python exports are `CDCChunker`, `CDCParams`, `Cache`, and `Chunk`. These exports are the supported library surface. Internal modules may change.

Documented CLI commands, exit codes, and existing JSON fields remain compatible within a minor release. Compatible releases may add JSON fields; consumers must ignore fields they do not recognize. A removal or meaning change requires release notes and a versioned migration path where persisted state is affected.

## Scope of the guarantee

Compatibility does not mean every configuration produces the same chunks. Parameters are identity inputs precisely so intentional changes remain detectable. It also does not turn the stateful TTTD rule into a formal fixed-distance locality guarantee; locality evidence and limits are documented separately.
