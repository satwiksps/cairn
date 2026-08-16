from __future__ import annotations

import json
from pathlib import Path

import pytest

from steadlith import _legacy_wire
from steadlith.cli import main
from steadlith.config import adopt_legacy_config, load_config
from steadlith.errors import ConfigError, ExitCode
from steadlith.index.service import apply_prepared, prepare_index


def test_v02_wire_identifiers_remain_frozen_in_one_compatibility_module() -> None:
    assert {
        "config": _legacy_wire.LEGACY_CONFIG_FILENAME,
        "state": _legacy_wire.LEGACY_STATE_DIRECTORY,
        "model": _legacy_wire.LEGACY_HASH_MODEL,
        "identity": _legacy_wire.V1_IDENTITY_SCHEMA,
        "normalizer": _legacy_wire.V1_NORMALIZER,
        "chunk_domain": _legacy_wire.V1_CHUNK_DOMAIN,
        "record_domain": _legacy_wire.V1_INDEX_RECORD_DOMAIN,
    } == {
        "config": "cairn.toml",
        "state": ".cairn",
        "model": "cairn-hash-256-v1",
        "identity": "cairn-chunk-identity-v1",
        "normalizer": "cairn-normalizer-v1",
        "chunk_domain": "cairn-chunk-v1",
        "record_domain": "cairn-index-record-v1",
    }


def _write_v02_project(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text(
        " ".join(f"word-{index}" for index in range(220)), encoding="utf-8"
    )
    legacy = tmp_path / "cairn.toml"
    legacy.write_text(
        """\
[chunker]
strategy = "cdc-rabin"
window_words = 48
min_tokens = 180
max_tokens = 640
snap_window_words = 24
primary_mask_bits = 8
backup_mask_bits = 6

[embedding]
provider = "hash"
model = "cairn-hash-256-v1"
dimensions = 256
batch_size = 64
price_per_million_tokens = 0.0

[store]
cache = ".cairn/cache.sqlite3"

[index]
backend = "sqlite"
database = ".cairn/index.sqlite3"

[sources]
include = ["docs/*.md"]
exclude = ["**/.git/**", "**/.cairn/**"]
""",
        encoding="utf-8",
    )
    return legacy


def test_adoption_reuses_v02_index_and_cache_without_reembedding(tmp_path: Path) -> None:
    legacy_path = _write_v02_project(tmp_path)
    legacy = load_config(legacy_path)
    first = apply_prepared(prepare_index(legacy))
    assert first.embedded_chunks > 0

    adopted_path = adopt_legacy_config(legacy_path, tmp_path / "steadlith.toml")
    adopted = load_config(adopted_path)
    prepared = prepare_index(adopted)

    assert adopted.embedding == legacy.embedding
    assert adopted.resolve(adopted.store.cache) == legacy.resolve(legacy.store.cache)
    assert adopted.resolve(adopted.index.database) == legacy.resolve(legacy.index.database)
    assert prepared.plan.requires_apply is False
    assert prepared.plan.cost.chunks_to_embed == 0
    no_op = apply_prepared(prepared)
    assert no_op.embedded_chunks == 0
    assert no_op.cache_hits == 0
    rendered = adopted_path.read_text(encoding="utf-8")
    assert rendered.startswith("# Steadlith configuration adopted from an earlier release.")
    assert "Cairn" not in rendered


def test_default_load_points_to_explicit_adoption_when_v02_config_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_v02_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ConfigError, match=r"without rebuilding state.*steadlith adopt"):
        load_config()


def test_cli_adopt_reports_that_state_paths_are_preserved(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    legacy_path = _write_v02_project(tmp_path)
    destination = tmp_path / "steadlith.toml"

    assert (
        main(
            [
                "adopt",
                "--from-config",
                str(legacy_path),
                "--config",
                str(destination),
                "--json",
            ]
        )
        == ExitCode.SUCCESS
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["configured_state_paths_preserved"] is True
    assert payload["state_moved"] is False
    assert payload["embeddings_created"] is False


def test_adoption_never_overwrites_or_changes_relative_path_base(tmp_path: Path) -> None:
    legacy_path = _write_v02_project(tmp_path)
    destination = tmp_path / "steadlith.toml"
    destination.write_text("sentinel\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="Refusing to overwrite"):
        adopt_legacy_config(legacy_path, destination)
    assert destination.read_text(encoding="utf-8") == "sentinel\n"

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    with pytest.raises(ConfigError, match="same directory"):
        adopt_legacy_config(legacy_path, elsewhere / "steadlith.toml")


def test_explicit_adoption_applies_v02_defaults_to_a_custom_config_name(tmp_path: Path) -> None:
    source = tmp_path / "project.toml"
    source.write_text('[sources]\ninclude = ["docs/*.md"]\n', encoding="utf-8")

    adopted_path = adopt_legacy_config(source, tmp_path / "steadlith.toml")
    adopted = load_config(adopted_path)

    assert adopted.embedding.model == _legacy_wire.LEGACY_HASH_MODEL
    assert adopted.store.cache == _legacy_wire.LEGACY_CACHE_PATH
    assert adopted.index.database == _legacy_wire.LEGACY_INDEX_PATH
    assert adopted.sources.exclude == _legacy_wire.LEGACY_SOURCE_EXCLUDE
