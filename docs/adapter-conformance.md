# Vector adapter status

Steadlith 1.0 supports one vector-index implementation: the local SQLite
adapter. The repository does not provide a backend registry, capability record,
conformance levels, or a shared parameterized adapter suite.

## SQLite behavior

The SQLite adapter:

- stores duplicate content as distinct indexed occurrences;
- excludes tombstoned records from queries;
- rejects stale generations and manifest roots during apply;
- commits an index snapshot in one SQLite transaction;
- verifies active records against the authoritative manifest; and
- compacts only eligible tombstoned rows.

These behaviors are exercised by `tests/test_sqlite_adapter.py` and
`tests/test_index_service.py`. The deployment limits in
[Backends and providers](backends-and-providers.md) still apply.

## Additional backends

No other vector backend is implemented or supported. A future backend would
need tests for the same observable behavior before its support could be claimed;
this repository does not contain that reusable test harness today.
