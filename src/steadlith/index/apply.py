"""Resolve stable vector-row identities from a manifest plan."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from steadlith._legacy_wire import V1_INSTANCE_PREFIX
from steadlith.index.adapters.base import IndexRecord
from steadlith.index.plan import IndexPlan, OperationKind


@dataclass(frozen=True)
class ResolvedIdentity:
    instance_id: str
    previous: IndexRecord | None


def new_instance_id(
    *,
    corpus_root: str,
    document_id: str,
    position: int,
    chunk_hash: str,
    identity_scope: str = "",
) -> str:
    """Derive a repeatable ID for a newly added occurrence without touching state."""

    digest = hashlib.sha256()
    digest.update(V1_INSTANCE_PREFIX)
    for value in (identity_scope, corpus_root, document_id, str(position), chunk_hash):
        digest.update(value.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()[:32]


def resolve_identities(
    plan: IndexPlan,
    current: Sequence[IndexRecord],
    *,
    identity_scope: str = "",
) -> Mapping[tuple[str, int], ResolvedIdentity]:
    """Carry row IDs through keep/move operations and assign IDs only to adds."""

    old_rows = {
        (record.document_id, record.position, record.chunk_hash): record for record in current
    }
    resolved: dict[tuple[str, int], ResolvedIdentity] = {}
    for operation in plan.operations:
        if operation.new_position is None:
            continue
        previous = None
        if operation.kind in {OperationKind.KEEP, OperationKind.MOVE}:
            if operation.old_position is not None:
                previous = old_rows.get(
                    (operation.document_id, operation.old_position, operation.chunk_hash)
                )
        instance_id = (
            previous.instance_id
            if previous is not None
            else new_instance_id(
                corpus_root=plan.new_root,
                document_id=operation.document_id,
                position=operation.new_position,
                chunk_hash=operation.chunk_hash,
                identity_scope=identity_scope,
            )
        )
        resolved[(operation.document_id, operation.new_position)] = ResolvedIdentity(
            instance_id=instance_id, previous=previous
        )
    return resolved
