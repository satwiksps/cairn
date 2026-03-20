"""Price chunker and embedding-model migrations before applying them."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from cairn_rag.content.manifest import CorpusManifest
from cairn_rag.index.plan import IndexPlan, create_plan


@dataclass(frozen=True)
class MigrationPlan:
    plan: IndexPlan
    chunker_changed: bool
    embedding_changed: bool
    from_chunker: str
    to_chunker: str
    from_model: str
    to_model: str

    @property
    def requires_gold_evaluation(self) -> bool:
        return self.chunker_changed or self.embedding_changed

    def as_dict(self) -> dict[str, object]:
        return {
            "chunker_changed": self.chunker_changed,
            "embedding_changed": self.embedding_changed,
            "from_chunker": self.from_chunker,
            "to_chunker": self.to_chunker,
            "from_model": self.from_model,
            "to_model": self.to_model,
            "requires_gold_evaluation": self.requires_gold_evaluation,
            "plan": self.plan.as_dict(),
        }


def plan_migration(
    old: CorpusManifest | None,
    new: CorpusManifest,
    *,
    from_chunker: str,
    to_chunker: str,
    from_model: str,
    to_model: str,
    is_cached: Callable[[str], bool] | None = None,
    price_per_million_tokens: float | None = None,
) -> MigrationPlan:
    embedding_changed = from_model != to_model
    plan = create_plan(
        old,
        new,
        is_cached=is_cached,
        price_per_million_tokens=price_per_million_tokens,
        embed_all=embedding_changed,
    )
    return MigrationPlan(
        plan=plan,
        chunker_changed=from_chunker != to_chunker,
        embedding_changed=embedding_changed,
        from_chunker=from_chunker,
        to_chunker=to_chunker,
        from_model=from_model,
        to_model=to_model,
    )
