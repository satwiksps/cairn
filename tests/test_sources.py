from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from steadlith.errors import SteadlithError
from steadlith.index.sources import discover_sources, load_source, load_sources


def test_discovery_is_filtered_and_deterministic(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    drafts = docs / "drafts"
    drafts.mkdir(parents=True)
    (docs / "b.md").write_text("B", encoding="utf-8")
    (docs / "a.md").write_text("A", encoding="utf-8")
    (docs / "image.bin").write_bytes(b"\0binary")
    (drafts / "skip.md").write_text("draft", encoding="utf-8")
    paths = discover_sources(
        base_dir=tmp_path,
        inputs=("docs",),
        excludes=("**/drafts/**",),
    )
    assert [path.name for path in paths] == ["a.md", "b.md"]
    sources = load_sources(paths, base_dir=tmp_path)
    assert [source.document_id for source in sources] == ["docs/a.md", "docs/b.md"]


def test_recursive_excludes_also_match_directly_below_the_project_root(tmp_path: Path) -> None:
    root_drafts = tmp_path / "drafts"
    root_state = tmp_path / ".steadlith"
    nested_state = tmp_path / "docs" / ".steadlith"
    root_drafts.mkdir()
    root_state.mkdir()
    nested_state.mkdir(parents=True)
    (tmp_path / "guide.md").write_text("keep", encoding="utf-8")
    (root_drafts / "skip.md").write_text("skip", encoding="utf-8")
    (root_state / "manifest.json").write_text("{}", encoding="utf-8")
    (nested_state / "manifest.json").write_text("{}", encoding="utf-8")

    paths = discover_sources(
        base_dir=tmp_path,
        inputs=(".",),
        excludes=("**/drafts/**", "**/.steadlith/**"),
    )

    assert [path.relative_to(tmp_path).as_posix() for path in paths] == ["guide.md"]


def test_sources_cannot_escape_the_configuration_directory(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "secret.md"
    outside.write_text("secret", encoding="utf-8")

    with pytest.raises(SteadlithError, match="escapes the configuration directory"):
        discover_sources(base_dir=project, inputs=(outside,))
    with pytest.raises(SteadlithError, match="escapes the configuration directory"):
        discover_sources(base_dir=project, includes=("../secret.md",))


def test_source_symlink_cannot_escape_the_configuration_directory(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "secret.md"
    outside.write_text("secret", encoding="utf-8")
    link = project / "linked.md"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable on this platform")

    with pytest.raises(SteadlithError, match="escapes the configuration directory"):
        discover_sources(base_dir=project, includes=("*.md",))


def test_source_change_during_read_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "guide.md"
    source.write_text("original", encoding="utf-8")
    original_read = Path.read_bytes

    def changing_read(path: Path) -> bytes:
        payload = original_read(path)
        path.write_text("changed while reading", encoding="utf-8")
        return payload

    monkeypatch.setattr(Path, "read_bytes", changing_read)
    with pytest.raises(SteadlithError, match="changed while it was being read"):
        load_source(source, base_dir=tmp_path)


def test_relocated_source_keeps_project_relative_metadata(tmp_path: Path) -> None:
    original = tmp_path / "original"
    relocated = tmp_path / "relocated"
    source_path = original / "docs" / "guide.md"
    relocated_path = relocated / "docs" / "guide.md"
    source_path.parent.mkdir(parents=True)
    relocated_path.parent.mkdir(parents=True)
    source_path.write_text("stable source", encoding="utf-8")
    shutil.copy2(source_path, relocated_path)

    source = load_source(source_path, base_dir=original)
    moved = load_source(relocated_path, base_dir=relocated)

    assert source.metadata == moved.metadata
    assert source.metadata["path"] == "docs/guide.md"
