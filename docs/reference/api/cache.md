# Cache API

```{autoclass} steadlith.Cache
:members: available, close, contains, get, get_many, put, put_many, stats, prune, export_jsonl, import_jsonl
```

```{autoclass} steadlith.store.cache.CacheStats
:members:
```

Cache import is safe only for authenticated artifacts. The `trusted=True` argument records explicit caller consent; it does not verify a signature.
