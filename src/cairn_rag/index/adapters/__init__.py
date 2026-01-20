"""Vector-index adapter interfaces and the built-in SQLite adapter."""

from cairn_rag.index.adapters.base import (
    ActiveRecord,
    DocumentState,
    IndexAdapter,
    IndexRecord,
    IndexStatus,
    VectorMatch,
)
from cairn_rag.index.adapters.sqlite import SQLiteIndex

__all__ = [
    "ActiveRecord",
    "DocumentState",
    "IndexAdapter",
    "IndexRecord",
    "IndexStatus",
    "SQLiteIndex",
    "VectorMatch",
]
