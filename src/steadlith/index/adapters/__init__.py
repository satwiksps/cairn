"""Vector-index adapter interfaces and the built-in SQLite adapter."""

from steadlith.index.adapters.base import (
    ActiveRecord,
    DocumentState,
    IndexAdapter,
    IndexRecord,
    IndexStatus,
    VectorMatch,
)
from steadlith.index.adapters.sqlite import SQLiteIndex

__all__ = [
    "ActiveRecord",
    "DocumentState",
    "IndexAdapter",
    "IndexRecord",
    "IndexStatus",
    "SQLiteIndex",
    "VectorMatch",
]
