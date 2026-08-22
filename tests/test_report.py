from __future__ import annotations

import json
from io import BytesIO, StringIO, TextIOWrapper

from rich.console import Console

from steadlith.index.adapters import IndexStatus, VectorMatch
from steadlith.index.plan import CostEstimate, IndexPlan, OperationKind, PlanOperation
from steadlith.report import (
    json_output,
    render_cache_stats,
    render_mapping_rows,
    render_plan,
    render_query_matches,
    render_status,
)
from steadlith.store.cache import CacheStats


def test_json_output_is_plain_json_even_on_a_color_terminal() -> None:
    output = StringIO()
    console = Console(file=output, force_terminal=True, color_system="standard")
    json_output({"message": "[green]literal[/green]", "value": 1}, console=console)

    rendered = output.getvalue()
    assert "\x1b" not in rendered
    assert json.loads(rendered) == {"message": "[green]literal[/green]", "value": 1}


def test_json_output_is_safe_on_a_legacy_windows_code_page() -> None:
    raw = BytesIO()
    output = TextIOWrapper(raw, encoding="cp1252", errors="strict")
    console = Console(file=output, force_terminal=False, color_system=None)

    json_output({"source": "greater than or equal: ≥"}, console=console)
    output.flush()

    rendered = raw.getvalue().decode("cp1252")
    assert "\\u2265" in rendered
    assert json.loads(rendered) == {"source": "greater than or equal: ≥"}


def test_query_output_treats_indexed_text_as_literal() -> None:
    output = StringIO()
    console = Console(file=output, width=120, color_system=None)
    render_query_matches(
        [
            VectorMatch(
                score=1.0,
                chunk_hash="hash",
                text="[bold]literal source text[/bold]",
                document_id="docs/[guide].md",
                start_offset=0,
                end_offset=31,
                metadata={},
            )
        ],
        console=console,
    )

    rendered = output.getvalue()
    assert "[bold]literal source text[/bold]" in rendered
    assert "docs/[guide].md" in rendered


def test_plan_output_reports_operations_costs_and_target_state() -> None:
    output = StringIO()
    console = Console(file=output, width=120, color_system=None)
    operations = (
        PlanOperation(OperationKind.ADD, "docs/a.md", "add-one"),
        PlanOperation(OperationKind.ADD, "docs/b.md", "add-two"),
        PlanOperation(OperationKind.KEEP, "docs/a.md", "keep"),
        PlanOperation(OperationKind.MOVE, "docs/a.md", "move"),
        PlanOperation(OperationKind.DELETE, "docs/old.md", "delete"),
    )
    plan = IndexPlan(
        old_root="old-root",
        new_root="target-root",
        operations=operations,
        cost=CostEstimate(
            cache_hits=3,
            chunks_to_embed=2,
            tokens_to_embed=456,
            estimated_cost=0.1234567,
            naive_chunks_to_embed=9,
            naive_tokens_to_embed=1_234,
            naive_estimated_cost=1.25,
        ),
        old_chunks=3,
        new_chunks=4,
        requires_apply=True,
    )

    render_plan(plan, console=console)

    rendered = output.getvalue()
    rows = [" ".join(line.split()) for line in rendered.splitlines()]
    assert any(row.startswith("│ add ") and row.endswith(" 2 │") for row in rows)
    assert any(row.startswith("│ keep ") and row.endswith(" 1 │") for row in rows)
    assert any(row.startswith("│ move ") and row.endswith(" 1 │") for row in rows)
    assert any(row.startswith("│ delete ") and row.endswith(" 1 │") for row in rows)
    assert "2 embeddings needed | 3 cache hits | 456 tokens | ~$0.123457" in rendered
    assert "Naive document rebuild: 9 chunks, 1,234 tokens, ~$1.250000" in rendered
    assert "Target state: target-root" in rendered


def test_plan_output_marks_unknown_prices() -> None:
    output = StringIO()
    console = Console(file=output, width=120, color_system=None)
    plan = IndexPlan(
        old_root=None,
        new_root="target-root",
        operations=(),
        cost=CostEstimate(0, 0, 0, None, 0, 0, None),
        old_chunks=0,
        new_chunks=0,
        requires_apply=False,
    )

    render_plan(plan, console=console)

    assert output.getvalue().count("price unknown") == 2


def test_status_output_reports_counts_rate_and_literal_model_id() -> None:
    output = StringIO()
    console = Console(file=output, width=120, color_system=None)
    status = IndexStatus(
        corpus_root="corpus-root",
        generation=7,
        documents=1_234,
        active_chunks=5_678,
        tombstoned_chunks=9,
        hard_cuts=2,
        total_boundaries=8,
        model_id="[red]literal-model[/red]",
        params_hash="params",
    )

    render_status(status, console=console)

    rendered = output.getvalue()
    assert "corpus-root" in rendered
    assert "1,234" in rendered
    assert "5,678" in rendered
    assert "25.00%" in rendered
    assert "[red]literal-model[/red]" in rendered


def test_cache_stats_output_reports_every_counter() -> None:
    output = StringIO()
    console = Console(file=output, width=120, color_system=None)

    render_cache_stats(
        CacheStats(entries=1_234, chunks=987, models=6, bytes=65_536), console=console
    )

    rendered = output.getvalue()
    assert "Embedding cache" in rendered
    assert "1,234" in rendered
    assert "987" in rendered
    assert "6" in rendered
    assert "65,536" in rendered


def test_mapping_rows_output_handles_values_missing_columns_and_empty_input() -> None:
    output = StringIO()
    console = Console(file=output, width=120, color_system=None)

    render_mapping_rows(
        [{"name": "alpha", "count": 2}, {"name": "beta"}],
        title="Measurements",
        console=console,
    )
    render_mapping_rows([], title="Empty measurements", console=console)

    rendered = output.getvalue()
    assert "Measurements" in rendered
    assert "name" in rendered
    assert "count" in rendered
    assert "alpha" in rendered
    assert "beta" in rendered
    assert "Empty measurements: no rows" in rendered
