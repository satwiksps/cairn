from __future__ import annotations

from pathlib import Path

import pytest

from cairn_rag.config import load_config, write_default_config
from cairn_rag.errors import ConfigError


def test_default_config_round_trip(tmp_path: Path) -> None:
    path = write_default_config(tmp_path / "cairn.toml")
    config = load_config(path)
    assert config.chunker.strategy == "cdc-rabin"
    assert config.embedding.provider == "hash"
    assert config.resolve(config.store.cache) == (tmp_path / ".cairn/cache.sqlite3").resolve()


def test_default_config_is_not_overwritten(tmp_path: Path) -> None:
    path = write_default_config(tmp_path / "cairn.toml")
    with pytest.raises(ConfigError, match="Refusing to overwrite"):
        write_default_config(path)


def test_unknown_config_key_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "cairn.toml"
    path.write_text("[chunker]\nmagic = true\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="Unknown key"):
        load_config(path)


def test_unimplemented_index_namespace_settings_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "cairn.toml"
    path.write_text('[index]\ndatabase = "index.sqlite3"\ncollection = "docs"\n', encoding="utf-8")
    with pytest.raises(ConfigError, match="Unknown key.*collection"):
        load_config(path)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ('[sources]\ninclude = "docs/*.md"\n', "array of strings"),
        ('[chunker]\nwindow_words = "48"\n', "must be integers"),
        ('[project]\nname = "typo"\n', "Unknown top-level"),
        ('[sources]\ninclude = ["../secret.md"]\n', "must stay below"),
        ('[store]\ncache = "../shared.sqlite3"\n', "must stay below"),
        (
            '[store]\ncache = ".cairn/state.sqlite3"\n[index]\ndatabase = ".cairn/state.sqlite3"\n',
            "must use different files",
        ),
        ("[embedding]\ndimensions = 65537\n", "must be between"),
        ("[embedding]\nprice_per_million_tokens = nan\n", "must be finite"),
        (
            '[embedding]\nprovider = "openai"\napi_key_env = "AWS_SECRET_ACCESS_KEY"\n',
            "only reads OPENAI_API_KEY",
        ),
        (
            '[embedding]\nprovider = "openai"\nbase_url = "https://attacker.invalid"\n',
            "base_url endpoints are disabled",
        ),
    ],
)
def test_invalid_config_types_and_tables_are_friendly(
    tmp_path: Path, payload: str, message: str
) -> None:
    path = tmp_path / "cairn.toml"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(ConfigError, match=message):
        load_config(path)
