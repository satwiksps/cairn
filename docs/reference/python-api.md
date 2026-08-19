# Python API

Steadlith's stable dependency-light library surface is deliberately small:

```python
from steadlith import CDCChunker, CDCParams, Cache, Chunk
```

These four exports follow the [compatibility policy](../compatibility.md). Internal modules are importable for advanced integrations, but they can change outside the top-level compatibility guarantee.

## Chunk text

```python
from steadlith import CDCChunker, CDCParams

params = CDCParams(
    window_words=48,
    min_tokens=180,
    max_tokens=640,
    primary_mask_bits=8,
    backup_mask_bits=6,
)
chunker = CDCChunker(params)

chunks = chunker.split(source_text, metadata={"source": "manual"})
for chunk in chunks:
    print(chunk.chunk_hash, chunk.start_offset, chunk.end_offset)
```

`Chunk` uses the common `page_content` and `metadata` shape. This keeps it compatible with document consumers without requiring LangChain or another framework in the core.

## Collect diagnostics

```python
result = chunker.split_with_stats(source_text)

print(result.stats.chunk_count)
print(result.stats.hard_cuts)
print(result.stats.hard_cut_rate)
```

The `CDCChunker.last_stats` property reflects the most recent `split` or `split_with_stats` call on that instance. Do not share one mutable chunker instance when independent callers rely on `last_stats`.

## Load project configuration

```python
from steadlith import CDCChunker
from steadlith.config import load_config

config = load_config("steadlith.toml")
chunker = CDCChunker.from_config(config)
```

Only the CDC strategies can be constructed through `CDCChunker.from_config`. Use `steadlith.index.service.create_chunker` when an advanced integration must honor every configured baseline strategy.

## Use a custom token counter

Token counts influence boundaries and must have an explicit versioned identity:

```python
def count_for_model(word: str) -> int:
    return max(1, len(word.encode("utf-8")) // 4)

params = CDCParams(tokenizer_id="example-byte-estimate-v1")
chunker = CDCChunker(
    params,
    token_counter=count_for_model,
    tokenizer_id="example-byte-estimate-v1",
)
```

The default `word-v1` name is reserved for the built-in one-word counter. Passing a custom callable without a distinct ID is rejected to prevent hash collisions between different boundary rules.

## Work with the cache

```python
from steadlith import Cache

with Cache(".steadlith/cache.sqlite3") as cache:
    cache.put(
        chunk_hash="...",
        model_id="example-model",
        params_hash="...",
        vector=(0.1, 0.2, 0.3),
    )
    vector = cache.get("...", "example-model", "...")
```

Vectors must be finite, float32-representable, and within the dimension limit. Use a context manager so the SQLite handle is closed.

## Advanced indexing service

```python
from steadlith.config import load_config
from steadlith.index.service import apply_prepared, prepare_index, verify_index

config = load_config("steadlith.toml")
prepared = prepare_index(config)

if prepared.plan.requires_apply:
    result = apply_prepared(prepared)

valid, problems = verify_index(config)
```

The service API does not implement CLI safety gates for network and deletion consent. Applications must inspect `prepared.plan`, enforce their own authorization, and only then call `apply_prepared`.

See the generated API pages for signatures and data models.
