from __future__ import annotations

import json
from io import BytesIO, StringIO, TextIOWrapper

from rich.console import Console

from steadlith.index.adapters import VectorMatch
from steadlith.report import json_output, render_query_matches


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
