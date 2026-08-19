# Configuration reference

This page is the compact schema reference for `steadlith.toml`. Read [Configuration](../getting-started/configuration.md) for examples, selection guidance, and security notes.

## File rules

- Encoding: UTF-8.
- Format: TOML.
- Default path: `steadlith.toml`.
- Maximum migration-managed config size: 1 MiB.
- Relative path base: the configuration file's parent directory.
- Unknown top-level tables, unknown keys, invalid types, and non-finite numbers are rejected.
- A pending `<config>.migration.json` journal blocks ordinary config loading until explicit recovery.

## `[chunker]`

| Key | Type | Default | Validation |
| --- | --- | --- | --- |
| `strategy` | string | `cdc-rabin` | `cdc-rabin`, `cdc-rabin+snap`, `fixed`, `recursive`, or `semantic` |
| `window_words` | integer | `48` | at least 2 |
| `min_tokens` | integer | `180` | greater than 0 and less than `max_tokens` |
| `max_tokens` | integer | `640` | greater than `min_tokens` |
| `snap_window_words` | integer | `24` | at least 0 |
| `primary_mask_bits` | integer | `8` | greater than backup and at most 63 |
| `backup_mask_bits` | integer | `6` | at least 1 and below primary |

For baseline strategies, the shared size fields are mapped to that strategy's supported controls. `fixed` uses `max_tokens` as its non-overlapping chunk size. `recursive` and `semantic` use the configured minimum and maximum.

## `[embedding]`

| Key | Type | Default | Validation |
| --- | --- | --- | --- |
| `provider` | string | `hash` | `hash`, `openai`, or `sentence-transformers` |
| `model` | string | `steadlith-hash-256-v1` | non-empty |
| `dimensions` | integer | `256` | 1 through 65,536 |
| `batch_size` | integer | `64` | greater than 0 |
| `price_per_million_tokens` | number | omitted by API; generated file uses `0.0` | finite and at least 0 |
| `api_key_env` | string | omitted | OpenAI only; exactly `OPENAI_API_KEY` |
| `base_url` | string | omitted | custom value rejected |

When price is omitted, plan cost fields are `null`. A zero value produces a numeric zero estimate.

## `[store]`

| Key | Type | Default | Validation |
| --- | --- | --- | --- |
| `cache` | string | `.steadlith/cache.sqlite3` | non-empty path below config directory; distinct from index database |

## `[index]`

| Key | Type | Default | Validation |
| --- | --- | --- | --- |
| `backend` | string | `sqlite` | exactly `sqlite` |
| `database` | string | `.steadlith/index.sqlite3` | non-empty path below config directory; distinct from cache |

## `[sources]`

| Key | Type | Default | Validation |
| --- | --- | --- | --- |
| `include` | array of strings | `docs/**/*.md`, `README.md` | non-empty relative patterns without `..` |
| `exclude` | array of strings | drafts, `.git`, `.steadlith` | non-empty relative patterns without `..` |

Patterns beginning with `**/` match both the project root and nested directories. Source symlinks are resolved and must remain below the configuration directory.

## Supported text suffixes

```text
.c .cc .cfg .conf .cpp .css .csv .go .h .hpp .html .ini .java
.js .json .jsx .md .mdx .php .py .rb .rs .rst .sh .sql .tex
.toml .ts .tsx .txt .xml .yaml .yml
```

Suffix matching is case-insensitive. A supported suffix does not override UTF-8 and binary-content checks.

## Programmatic loading

```python
from steadlith.config import load_config

config = load_config("steadlith.toml")
print(config.base_dir)
print(config.resolve(config.index.database))
```

`load_config` returns a validated frozen `SteadlithConfig`. Use `with_chunker` and `with_embedding` for validated in-memory copies rather than mutating nested objects.
