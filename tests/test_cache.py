from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cairn_rag.errors import BackendError
from cairn_rag.store import Cache


def test_cache_key_separates_embedding_models(tmp_path: Path) -> None:
    path = tmp_path / "cache.sqlite3"
    with Cache(path) as cache:
        cache.put("chunk", "model-a", "params", [1.0, 0.0], token_count=4)
        cache.put("chunk", "model-b", "params", [0.0, 1.0], token_count=4)
        assert cache.get("chunk", "model-a", "params") == pytest.approx((1.0, 0.0))
        assert cache.get("chunk", "model-b", "params") == pytest.approx((0.0, 1.0))
        assert cache.stats().entries == 2


def test_cache_get_many_deduplicates_keys_and_returns_hits(tmp_path: Path) -> None:
    key = ("chunk", "model", "params")
    with Cache(tmp_path / "cache.sqlite3") as cache:
        cache.put(*key, (1.0, 0.0), token_count=2)
        assert cache.get_many([key, key]) == {key: pytest.approx((1.0, 0.0))}


def test_cache_get_many_batches_above_sqlite_parameter_limit(tmp_path: Path) -> None:
    keys = [(f"chunk-{index}", "model", "params") for index in range(251)]
    with Cache(tmp_path / "cache.sqlite3") as cache:
        cache.put_many((*key, (float(index),), 1) for index, key in enumerate(keys))
        found = cache.get_many(keys)
    assert len(found) == len(keys)
    assert found[keys[-1]] == pytest.approx((250.0,))


def test_cache_export_import_round_trip(tmp_path: Path) -> None:
    export = tmp_path / "cache.jsonl"
    with Cache(tmp_path / "one.sqlite3") as source:
        source.put("abc", "local:test", "p1", [0.25, -0.5], token_count=7)
        assert source.export_jsonl(export) == 1
    with Cache(tmp_path / "two.sqlite3") as target:
        assert target.import_jsonl(export, trusted=True) == 1
        assert target.get("abc", "local:test", "p1") == pytest.approx((0.25, -0.5))


def test_readonly_missing_cache_is_empty(tmp_path: Path) -> None:
    with Cache(tmp_path / "missing.sqlite3", readonly=True) as cache:
        assert cache.get("x", "m", "p") is None
        assert cache.stats().entries == 0


@pytest.mark.parametrize("argument", [{"max_age_days": -1}, {"max_entries": -1}])
def test_cache_prune_rejects_negative_limits(tmp_path: Path, argument: dict[str, int]) -> None:
    with Cache(tmp_path / "cache.sqlite3") as cache:
        with pytest.raises(ValueError, match="non-negative"):
            cache.prune(**argument)


def test_export_of_missing_readonly_cache_creates_parent(tmp_path: Path) -> None:
    destination = tmp_path / "nested" / "cache.jsonl"
    with Cache(tmp_path / "missing.sqlite3", readonly=True) as cache:
        assert cache.export_jsonl(destination) == 0
    assert destination.read_text(encoding="utf-8") == ""


@pytest.mark.parametrize("vector", [(), (float("nan"),), (float("inf"),)])
def test_cache_rejects_empty_or_non_finite_vectors(
    tmp_path: Path, vector: tuple[float, ...]
) -> None:
    with Cache(tmp_path / "cache.sqlite3") as cache:
        with pytest.raises(BackendError, match="non-empty and finite"):
            cache.put("chunk", "model", "params", vector)


def test_cache_key_cannot_be_overwritten_with_an_incompatible_vector(tmp_path: Path) -> None:
    with Cache(tmp_path / "cache.sqlite3") as cache:
        cache.put("chunk", "model", "params", (1.0, 0.0), token_count=2)
        with pytest.raises(BackendError, match="incompatible embedding"):
            cache.put("chunk", "model", "params", (0.0, 1.0), token_count=2)
        assert cache.get("chunk", "model", "params") == pytest.approx((1.0, 0.0))


def test_cache_export_cannot_overwrite_live_database_or_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "cache.sqlite3"
    export = tmp_path / "cache.jsonl"
    with Cache(path) as cache:
        cache.put("chunk", "model", "params", (1.0,), token_count=1)
        original_size = path.stat().st_size
        with pytest.raises(BackendError, match="live cache"):
            cache.export_jsonl(path, force=True)
        assert path.stat().st_size == original_size

        export.write_text("existing", encoding="utf-8")
        with pytest.raises(BackendError, match="Refusing to overwrite"):
            cache.export_jsonl(export)
        assert export.read_text(encoding="utf-8") == "existing"
        assert cache.export_jsonl(export, force=True) == 1


def test_unsigned_cache_import_requires_explicit_trust(tmp_path: Path) -> None:
    source = tmp_path / "cache.jsonl"
    source.write_text("", encoding="utf-8")
    with Cache(tmp_path / "cache.sqlite3") as cache:
        with pytest.raises(BackendError, match="explicitly trust"):
            cache.import_jsonl(source)


def test_cache_rejects_float32_overflow(tmp_path: Path) -> None:
    with Cache(tmp_path / "cache.sqlite3") as cache:
        with pytest.raises(BackendError, match="float32 range"):
            cache.put("chunk", "model", "params", (1e100,))


def test_cache_rejects_excessive_vector_dimensions(tmp_path: Path) -> None:
    with Cache(tmp_path / "cache.sqlite3") as cache:
        with pytest.raises(BackendError, match="cannot exceed"):
            cache.put("chunk", "model", "params", [0.0] * 65_537)


def test_invalid_cache_schema_version_is_a_typed_backend_error(tmp_path: Path) -> None:
    path = tmp_path / "cache.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE cache_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO cache_meta VALUES ('schema_version', 'broken')")
    with pytest.raises(BackendError, match="Invalid cache schema version"):
        Cache(path)
    with pytest.raises(BackendError, match="Invalid cache schema version"):
        Cache(path, readonly=True)


def test_cache_import_rejects_invalid_encoding_and_live_database(tmp_path: Path) -> None:
    path = tmp_path / "cache.sqlite3"
    invalid = tmp_path / "invalid.jsonl"
    invalid.write_bytes(b"\xff\xfe")
    with Cache(path) as cache:
        with pytest.raises(BackendError, match="Could not read cache export"):
            cache.import_jsonl(invalid, trusted=True)
        with pytest.raises(BackendError, match="live cache"):
            cache.import_jsonl(path, trusted=True)
