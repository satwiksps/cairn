from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from steadlith.cli import main
from steadlith.errors import BackendError, ExitCode
from steadlith.index.adapters import SQLiteIndex
from steadlith.store import Cache


def _files(root: Path) -> dict[Path, bytes]:
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


@pytest.mark.parametrize(
    ("open_backend", "filename"),
    [
        pytest.param(Cache, "cache.sqlite3", id="cache"),
        pytest.param(SQLiteIndex, "index.sqlite3", id="index"),
    ],
)
def test_state_backend_reports_a_file_blocking_its_parent_without_mutation(
    tmp_path: Path,
    open_backend: Callable[[Path], object],
    filename: str,
) -> None:
    state_directory = tmp_path / ".steadlith"
    state_directory.write_bytes(b"keep this file")
    before = _files(tmp_path)

    with pytest.raises(BackendError) as raised:
        open_backend(state_directory / "nested" / filename)

    message = str(raised.value)
    assert str(state_directory.resolve()) in message
    assert "rename" in message.lower()
    assert "configure" in message.lower()
    assert _files(tmp_path) == before


@pytest.mark.parametrize(
    ("open_backend", "filename"),
    [
        pytest.param(Cache, "cache.sqlite3", id="cache"),
        pytest.param(SQLiteIndex, "index.sqlite3", id="index"),
    ],
)
def test_readonly_state_backend_reports_a_file_blocking_its_parent_without_mutation(
    tmp_path: Path,
    open_backend: Callable[..., object],
    filename: str,
) -> None:
    state_directory = tmp_path / ".steadlith"
    state_directory.write_bytes(b"keep this file")
    before = _files(tmp_path)

    with pytest.raises(BackendError) as raised:
        open_backend(state_directory / "nested" / filename, readonly=True)

    message = str(raised.value)
    assert str(state_directory.resolve()) in message
    assert "rename" in message.lower()
    assert "configure" in message.lower()
    assert _files(tmp_path) == before


@pytest.mark.parametrize("command", ["cache", "index"])
def test_cli_reports_a_file_blocking_the_state_directory_without_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    command: str,
) -> None:
    config = tmp_path / "steadlith.toml"
    source = tmp_path / "source.txt"
    source.write_text("state path collision evidence", encoding="utf-8")
    assert main(["init", "--config", str(config), "--json"]) == ExitCode.SUCCESS
    capsys.readouterr()

    state_directory = tmp_path / ".steadlith"
    state_directory.write_bytes(b"keep this file")
    before = _files(tmp_path)
    arguments = (
        ["cache", "prune", "--max-entries", "0"] if command == "cache" else ["index", str(source)]
    )

    assert (
        main([*arguments, "--config", str(config), "--json"]) == ExitCode.BACKEND_OR_PROVIDER_ERROR
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["error_type"] == "BackendError"
    assert str(state_directory.resolve()) in payload["error"]
    assert "rename" in payload["error"].lower()
    assert "configure" in payload["error"].lower()
    assert _files(tmp_path) == before


@pytest.mark.parametrize(
    "arguments",
    [
        pytest.param(["status"], id="status"),
        pytest.param(["plan"], id="plan"),
        pytest.param(["compact", "--dry-run"], id="compact-dry-run"),
    ],
)
def test_readonly_cli_reports_a_file_blocking_the_state_directory_without_mutation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
) -> None:
    config = tmp_path / "steadlith.toml"
    assert main(["init", "--config", str(config), "--json"]) == ExitCode.SUCCESS
    capsys.readouterr()

    state_directory = tmp_path / ".steadlith"
    state_directory.write_bytes(b"keep this file")
    before = _files(tmp_path)

    assert (
        main([*arguments, "--config", str(config), "--json"]) == ExitCode.BACKEND_OR_PROVIDER_ERROR
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["error_type"] == "BackendError"
    assert str(state_directory.resolve()) in payload["error"]
    assert "rename" in payload["error"].lower()
    assert "configure" in payload["error"].lower()
    assert _files(tmp_path) == before
