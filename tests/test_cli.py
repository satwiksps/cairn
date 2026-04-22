from __future__ import annotations

import json
import sys
from io import BytesIO, TextIOWrapper
from pathlib import Path

import pytest

from cairn_rag.cli import main
from cairn_rag.errors import ExitCode


def test_init_status_and_verify_exit_codes(tmp_path: Path) -> None:
    config = tmp_path / "cairn.toml"
    assert main(["init", "--config", str(config)]) == ExitCode.SUCCESS
    assert main(["status", "--config", str(config), "--json"]) == ExitCode.SUCCESS
    assert main(["verify", "--config", str(config), "--json"]) == ExitCode.VERIFICATION_MISMATCH


def test_init_json_is_machine_readable(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = tmp_path / "cairn.toml"

    assert main(["init", "--config", str(config), "--json"]) == ExitCode.SUCCESS

    payload = json.loads(capsys.readouterr().out)
    assert payload["created"] == str(config.resolve())
    assert payload["backend"] == "sqlite"


def test_human_output_survives_a_legacy_windows_code_page(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = BytesIO()
    output = TextIOWrapper(raw, encoding="cp1252", errors="strict")
    monkeypatch.setattr(sys, "stdout", output)
    config = tmp_path / "cairn-≥.toml"

    assert main(["init", "--config", str(config)]) == ExitCode.SUCCESS
    output.flush()

    rendered = raw.getvalue().decode("cp1252")
    assert "cairn-\\u2265.toml" in rendered


def test_missing_config_uses_config_exit_code(tmp_path: Path) -> None:
    missing = tmp_path / "missing.toml"
    assert main(["plan", "--config", str(missing)]) == ExitCode.CONFIG_ERROR


def test_json_errors_remain_machine_readable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "missing.toml"
    assert main(["query", "hello", "--config", str(missing), "--json"]) == ExitCode.CONFIG_ERROR
    payload = json.loads(capsys.readouterr().out)
    assert payload["error_type"] == "ConfigError"
    assert payload["exit_code"] == ExitCode.CONFIG_ERROR
    assert "Configuration not found" in payload["error"]


def test_compact_rejects_ambiguous_or_invalid_cutoff(tmp_path: Path) -> None:
    config = tmp_path / "cairn.toml"
    assert main(["init", "--config", str(config)]) == ExitCode.SUCCESS
    assert (
        main(["compact", "--before", "2026-08-15", "--config", str(config)])
        == ExitCode.CONFIG_ERROR
    )
    assert main(["compact", "--before", "zzz", "--config", str(config)]) == ExitCode.CONFIG_ERROR


def test_migration_apply_requires_an_existing_index(tmp_path: Path) -> None:
    config = tmp_path / "cairn.toml"
    assert main(["init", "--config", str(config)]) == ExitCode.SUCCESS

    assert (
        main(
            [
                "migrate",
                "--embedding-model",
                "replacement-model",
                "--apply",
                "--config",
                str(config),
            ]
        )
        == ExitCode.CONFIG_ERROR
    )
    assert not (tmp_path / ".cairn/index.sqlite3").exists()


@pytest.mark.parametrize(
    "arguments",
    [
        ["measure", "churn", "--price", "-1", "--json"],
        ["measure", "churn", "--price", "nan", "--json"],
        ["measure", "retrieval", "-k", "0", "--json"],
    ],
)
def test_measurement_argument_errors_are_typed(arguments: list[str]) -> None:
    assert main(arguments) == ExitCode.CONFIG_ERROR


def test_index_requires_explicit_deletion_and_empty_corpus_confirmation(tmp_path: Path) -> None:
    config = tmp_path / "cairn.toml"
    assert main(["init", "--config", str(config)]) == ExitCode.SUCCESS
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            'include = ["docs/**/*.md", "README.md"]', 'include = ["docs/*.md"]'
        ),
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    source = docs / "guide.md"
    source.write_text(" ".join(f"word-{index}" for index in range(200)), encoding="utf-8")
    assert main(["index", "--config", str(config), "--json"]) == ExitCode.SUCCESS

    source.unlink()
    assert main(["index", "--config", str(config), "--json"]) == ExitCode.CONFIG_ERROR
    assert (
        main(["index", "--allow-delete", "--config", str(config), "--json"])
        == ExitCode.CONFIG_ERROR
    )
    assert (
        main(
            [
                "index",
                "--allow-delete",
                "--allow-empty",
                "--config",
                str(config),
                "--json",
            ]
        )
        == ExitCode.SUCCESS
    )


def test_non_demo_provider_requires_explicit_network_confirmation(tmp_path: Path) -> None:
    config = tmp_path / "cairn.toml"
    config.write_text(
        '[embedding]\nprovider = "openai"\nmodel = "text-embedding-test"\n',
        encoding="utf-8",
    )
    assert main(["index", "--config", str(config), "--json"]) == ExitCode.CONFIG_ERROR
    assert main(["query", "hello", "--config", str(config), "--json"]) == ExitCode.CONFIG_ERROR


def test_query_returns_machine_readable_active_results(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "cairn.toml"
    assert main(["init", "--config", str(config)]) == ExitCode.SUCCESS
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            'include = ["docs/**/*.md", "README.md"]', 'include = ["docs/*.md"]'
        ),
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text(
        " ".join([*("ordinary" for _ in range(190)), "quartz", "needle", "quartz"]),
        encoding="utf-8",
    )
    assert main(["index", "--config", str(config), "--json"]) == ExitCode.SUCCESS
    capsys.readouterr()

    assert (
        main(
            [
                "query",
                "quartz needle",
                "--limit",
                "2",
                "--config",
                str(config),
                "--json",
            ]
        )
        == ExitCode.SUCCESS
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["query"] == "quartz needle"
    assert payload["count"] >= 1
    assert len(payload["matches"]) <= 2
    assert payload["matches"][0]["document_id"] == "docs/guide.md"
    assert "quartz needle" in payload["matches"][0]["text"]


def test_query_argument_errors_are_typed(tmp_path: Path) -> None:
    config = tmp_path / "cairn.toml"
    assert main(["init", "--config", str(config)]) == ExitCode.SUCCESS
    assert (
        main(["query", "hello", "--limit", "0", "--config", str(config)]) == ExitCode.CONFIG_ERROR
    )


def test_status_distinguishes_embedding_identity_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "cairn.toml"
    assert main(["init", "--config", str(config)]) == ExitCode.SUCCESS
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            'include = ["docs/**/*.md", "README.md"]', 'include = ["docs/*.md"]'
        ),
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text(" ".join(f"word-{i}" for i in range(200)), encoding="utf-8")
    assert main(["index", "--config", str(config), "--json"]) == ExitCode.SUCCESS
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            'model = "cairn-hash-256-v1"', 'model = "cairn-hash-256-v2"'
        ),
        encoding="utf-8",
    )
    capsys.readouterr()

    assert main(["status", "--config", str(config), "--json"]) == ExitCode.SUCCESS
    payload = json.loads(capsys.readouterr().out)
    assert payload["index_drift"] is True
    assert payload["source_drift"] is False
    assert payload["embedding_drift"] is True
    assert payload["pending_embeddings"] > 0
