"""Deterministic Merkle trees for document and corpus state."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from steadlith._legacy_wire import (
    V1_CORPUS_DOCUMENT_DOMAIN,
    V1_MERKLE_EMPTY_DOMAIN,
    V1_MERKLE_LEAF_DOMAIN,
    V1_MERKLE_NODE_DOMAIN,
)
from steadlith.content.hashing import hash_fields

EMPTY_MERKLE_ROOT = hash_fields(V1_MERKLE_EMPTY_DOMAIN, ())


def _leaf_hash(value: str) -> str:
    return hash_fields(V1_MERKLE_LEAF_DOMAIN, (value,))


def _parent_hash(left: str, right: str | None) -> str:
    return hash_fields(V1_MERKLE_NODE_DOMAIN, (left, right or ""))


@dataclass(frozen=True)
class MerkleTree:
    """An immutable binary Merkle tree preserving input order."""

    leaves: tuple[str, ...]
    levels: tuple[tuple[str, ...], ...]

    @classmethod
    def from_leaves(cls, leaves: Iterable[str]) -> MerkleTree:
        values = tuple(str(value) for value in leaves)
        if any(not value for value in values):
            raise ValueError("Merkle leaves cannot be empty strings")
        if not values:
            return cls((), ((EMPTY_MERKLE_ROOT,),))
        levels: list[tuple[str, ...]] = [tuple(_leaf_hash(value) for value in values)]
        current = levels[0]
        while len(current) > 1:
            parents = tuple(
                _parent_hash(
                    current[index], current[index + 1] if index + 1 < len(current) else None
                )
                for index in range(0, len(current), 2)
            )
            levels.append(parents)
            current = parents
        return cls(values, tuple(levels))

    @property
    def root(self) -> str:
        return self.levels[-1][0]

    @property
    def root_hash(self) -> str:
        return self.root

    def __len__(self) -> int:
        return len(self.leaves)

    def diff_indices(self, other: MerkleTree) -> tuple[int, ...]:
        """Find differing leaf positions, pruning equal subtrees."""

        if self.root == other.root and len(self) == len(other):
            return ()
        if len(self) != len(other):
            common = min(len(self), len(other))
            unequal_indices = [
                index for index in range(common) if self.leaves[index] != other.leaves[index]
            ]
            unequal_indices.extend(range(common, max(len(self), len(other))))
            return tuple(unequal_indices)

        changed: list[int] = []

        def descend(level: int, index: int) -> None:
            if self.levels[level][index] == other.levels[level][index]:
                return
            if level == 0:
                changed.append(index)
                return
            left = index * 2
            if left < len(self.levels[level - 1]):
                descend(level - 1, left)
            if left + 1 < len(self.levels[level - 1]):
                descend(level - 1, left + 1)

        descend(len(self.levels) - 1, 0)
        return tuple(changed)


def merkle_root(leaves: Iterable[str]) -> str:
    return MerkleTree.from_leaves(leaves).root


def document_root(chunk_hashes: Iterable[str]) -> str:
    return merkle_root(chunk_hashes)


def corpus_root(document_roots: Mapping[str, str] | Sequence[tuple[str, str]]) -> str:
    """Hash ordered ``(document_id, root)`` pairs into one verifiable state id."""

    items = document_roots.items() if isinstance(document_roots, Mapping) else document_roots
    leaves = (
        hash_fields(V1_CORPUS_DOCUMENT_DOMAIN, (document_id, root))
        for document_id, root in sorted(items, key=lambda item: item[0])
    )
    return merkle_root(leaves)


def changed_leaf_indices(old: Iterable[str], new: Iterable[str]) -> tuple[int, ...]:
    return MerkleTree.from_leaves(old).diff_indices(MerkleTree.from_leaves(new))
