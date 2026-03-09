"""Stable human and JSON output for the command-line interface."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.text import Text

from cairn_rag.index.adapters.base import IndexStatus, VectorMatch
from cairn_rag.index.plan import IndexPlan, OperationKind
from cairn_rag.store.cache import CacheStats


def json_output(payload: Any, *, console: Console) -> None:
    serialized = json.dumps(
        payload,
        sort_keys=True,
        default=str,
        # Keep machine output portable across redirected Windows consoles whose
        # legacy code page cannot encode arbitrary indexed source text.
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
    )
    console.print(serialized, markup=False, highlight=False, soft_wrap=True)


def render_plan(plan: IndexPlan, *, console: Console) -> None:
    counts = plan.counts
    table = Table(title="Index plan", show_header=True, header_style="bold")
    table.add_column("Operation")
    table.add_column("Chunks", justify="right")
    for kind in OperationKind:
        table.add_row(kind.value, f"{counts[kind]:,}")
    console.print(table)
    cost = plan.cost
    priced = f"~${cost.estimated_cost:,.6f}" if cost.estimated_cost is not None else "price unknown"
    naive_priced = (
        f"~${cost.naive_estimated_cost:,.6f}"
        if cost.naive_estimated_cost is not None
        else "price unknown"
    )
    console.print(
        f"[bold]{cost.chunks_to_embed:,}[/bold] embeddings needed | "
        f"{cost.cache_hits:,} cache hits | {cost.tokens_to_embed:,} tokens | {priced}"
    )
    console.print(
        f"Naive document rebuild: {cost.naive_chunks_to_embed:,} chunks, "
        f"{cost.naive_tokens_to_embed:,} tokens, {naive_priced}"
    )
    console.print(f"Target state: [dim]{plan.new_root}[/dim]")


def render_status(status: IndexStatus, *, console: Console) -> None:
    table = Table(title="Cairn index", show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Corpus root", status.corpus_root or "not indexed")
    table.add_row("Documents", f"{status.documents:,}")
    table.add_row("Active chunks", f"{status.active_chunks:,}")
    table.add_row("Tombstones", f"{status.tombstoned_chunks:,}")
    table.add_row(
        "Hard cuts",
        f"{status.hard_cuts:,} / {status.total_boundaries:,} ({status.hard_cut_rate:.2%})",
    )
    table.add_row("Embedding model", Text(status.model_id or "not set"))
    console.print(table)


def render_cache_stats(stats: CacheStats, *, console: Console) -> None:
    table = Table(title="Embedding cache", show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value", justify="right")
    table.add_row("Entries", f"{stats.entries:,}")
    table.add_row("Unique chunks", f"{stats.chunks:,}")
    table.add_row("Model configurations", f"{stats.models:,}")
    table.add_row("Vector bytes", f"{stats.bytes:,}")
    console.print(table)


def render_query_matches(matches: list[VectorMatch], *, console: Console) -> None:
    if not matches:
        console.print("[dim]No active chunks matched.[/dim]")
        return
    table = Table(title="Query results", show_header=True, header_style="bold")
    table.add_column("#", justify="right", no_wrap=True)
    table.add_column("Score", justify="right", no_wrap=True)
    table.add_column("Source", no_wrap=True)
    table.add_column("Offsets", justify="right", no_wrap=True)
    table.add_column("Text", overflow="fold")
    for rank, match in enumerate(matches, start=1):
        preview = " ".join(match.text.split())
        if len(preview) > 240:
            preview = f"{preview[:237]}..."
        table.add_row(
            str(rank),
            f"{match.score:.4f}",
            Text(match.document_id),
            f"{match.start_offset}:{match.end_offset}",
            Text(preview),
        )
    console.print(table)


def render_mapping_rows(rows: list[Mapping[str, Any]], *, title: str, console: Console) -> None:
    if not rows:
        console.print(f"[dim]{title}: no rows[/dim]")
        return
    columns = list(rows[0])
    table = Table(title=title)
    for column in columns:
        table.add_column(column, justify="right" if column != columns[0] else "left")
    for row in rows:
        table.add_row(*(str(row.get(column, "")) for column in columns))
    console.print(table)
