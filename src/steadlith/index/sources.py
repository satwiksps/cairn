"""Explicit source discovery and text loading for the I/O layer."""

from __future__ import annotations

import fnmatch
import os
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from steadlith.errors import SteadlithError

TEXT_SUFFIXES = frozenset(
    {
        ".c",
        ".cc",
        ".cfg",
        ".conf",
        ".cpp",
        ".css",
        ".csv",
        ".go",
        ".h",
        ".hpp",
        ".html",
        ".ini",
        ".java",
        ".js",
        ".json",
        ".jsx",
        ".md",
        ".mdx",
        ".php",
        ".py",
        ".rb",
        ".rs",
        ".rst",
        ".sh",
        ".sql",
        ".tex",
        ".toml",
        ".ts",
        ".tsx",
        ".txt",
        ".xml",
        ".yaml",
        ".yml",
    }
)


@dataclass(frozen=True)
class SourceDocument:
    document_id: str
    path: Path
    text: str
    mtime_ns: int
    size: int

    @property
    def metadata(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "mtime_ns": self.mtime_ns,
            "size": self.size,
        }


def _relative_id(path: Path, base_dir: Path) -> str:
    try:
        return path.relative_to(base_dir).as_posix()
    except ValueError:
        return path.as_posix()


def _require_below_base(path: Path, base_dir: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(base_dir)
    except ValueError as exc:
        raise SteadlithError(
            f"Source escapes the configuration directory {base_dir}: {resolved}"
        ) from exc
    return resolved


def _is_excluded(path: Path, base_dir: Path, patterns: Sequence[str]) -> bool:
    relative = _relative_id(path, base_dir)
    for configured in patterns:
        pattern = configured.replace("\\", "/")
        variants = [pattern]
        # Python's fnmatch treats ``**/`` as requiring at least one directory,
        # while source-glob users reasonably expect it to match zero or more.
        while pattern.startswith("**/"):
            pattern = pattern[3:]
            variants.append(pattern)
        if any(
            fnmatch.fnmatch(relative, variant)
            or fnmatch.fnmatch(path.name, variant)
            or Path(relative).match(variant)
            for variant in variants
        ):
            return True
    return False


def discover_sources(
    *,
    base_dir: Path,
    inputs: Sequence[str | Path] = (),
    includes: Sequence[str] = (),
    excludes: Sequence[str] = (),
) -> tuple[Path, ...]:
    """Resolve an explicit, deterministic list of supported text files."""

    base_dir = base_dir.expanduser().resolve()
    candidates: set[Path] = set()
    if inputs:
        for value in inputs:
            path = Path(value).expanduser()
            if not path.is_absolute():
                path = base_dir / path
            path = _require_below_base(path, base_dir)
            if not path.exists():
                raise SteadlithError(f"Source does not exist: {path}")
            if path.is_dir():
                candidates.update(
                    _require_below_base(item, base_dir)
                    for item in path.rglob("*")
                    if item.is_file()
                )
            elif path.is_file():
                candidates.add(path)
    else:
        for pattern in includes:
            candidates.update(
                _require_below_base(item, base_dir)
                for item in base_dir.glob(pattern)
                if item.is_file()
            )

    resolved = []
    for path in candidates:
        if path.suffix.casefold() not in TEXT_SUFFIXES:
            continue
        if _is_excluded(path, base_dir, excludes):
            continue
        resolved.append(path)
    return tuple(sorted(resolved, key=lambda item: _relative_id(item, base_dir)))


def load_source(path: Path, *, base_dir: Path) -> SourceDocument:
    """Read one UTF-8 source and retain filesystem metadata for drift checks."""

    base_dir = base_dir.expanduser().resolve()
    path = _require_below_base(path, base_dir)
    try:
        before = path.stat()
        payload = path.read_bytes()
        stat = path.stat()
    except OSError as exc:
        raise SteadlithError(f"Could not read source {path}: {exc}") from exc
    before_identity = (before.st_mtime_ns, before.st_size, getattr(before, "st_ino", None))
    after_identity = (stat.st_mtime_ns, stat.st_size, getattr(stat, "st_ino", None))
    if before_identity != after_identity:
        raise SteadlithError(f"Source changed while it was being read; retry the operation: {path}")
    if b"\0" in payload[:8192]:
        raise SteadlithError(f"Binary source is not supported: {path}")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SteadlithError(f"Source is not valid UTF-8: {path}: {exc}") from exc
    return SourceDocument(
        document_id=_relative_id(path, base_dir),
        path=path,
        text=text,
        mtime_ns=stat.st_mtime_ns,
        size=stat.st_size,
    )


def load_sources(paths: Iterable[Path], *, base_dir: Path) -> tuple[SourceDocument, ...]:
    documents = tuple(load_source(path, base_dir=base_dir) for path in paths)
    ids = [document.document_id for document in documents]
    if len(ids) != len(set(ids)):
        duplicates = sorted({document_id for document_id in ids if ids.count(document_id) > 1})
        raise SteadlithError(f"Duplicate source identifiers: {', '.join(duplicates)}")
    return documents


def source_drift(source: SourceDocument, metadata: dict[str, object]) -> bool:
    """Cheap drift check used by status; content is re-read only for planning."""

    def stored_int(key: str) -> int:
        value = metadata.get(key)
        if isinstance(value, bool):
            return -1
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return -1
        return -1

    path_value = metadata.get("path")
    stored_path = os.fspath(path_value) if isinstance(path_value, (str, os.PathLike)) else ""
    return bool(
        stored_int("mtime_ns") != source.mtime_ns
        or stored_int("size") != source.size
        or stored_path != os.fspath(source.path)
    )
