"""Shared SQLite timestamp and float-vector values."""

from __future__ import annotations

import stat
import struct
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from steadlith.errors import BackendError


def find_blocking_parent(path: Path) -> Path | None:
    candidate = path.parent
    while True:
        try:
            mode = candidate.stat().st_mode
        except (FileNotFoundError, NotADirectoryError):
            parent = candidate.parent
            if parent == candidate:
                return None
            candidate = parent
            continue
        return None if stat.S_ISDIR(mode) else candidate


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def encode_vector(vector: Sequence[float]) -> bytes:
    if not vector:
        return b""
    return struct.pack(f"<{len(vector)}f", *(float(value) for value in vector))


def decode_vector(payload: bytes, dimensions: int, *, corrupt_message: str) -> tuple[float, ...]:
    if dimensions == 0:
        return ()
    if len(payload) != dimensions * 4:
        raise BackendError(corrupt_message)
    return tuple(struct.unpack(f"<{dimensions}f", payload))
