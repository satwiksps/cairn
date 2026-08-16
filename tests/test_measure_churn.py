from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import pytest

from steadlith.measure.churn import (
    DEFAULT_STRATEGY_NAMES,
    EmbeddingPrice,
    benchmark_churn,
    measure_churn,
    measure_corpus_churn,
    snapshot_chunks,
)
from steadlith.measure.corpora import EditOperation, get_corpus


class PipeChunker:
    def split(self, text: str, metadata: Mapping[str, Any] | None = None) -> list[str]:
        del metadata
        return [] if not text else text.split("|")


@dataclass(frozen=True)
class ShapedChunk:
    page_content: str
    chunk_hash: str
    token_count: int


def test_churn_uses_multiset_hashes_and_prices_only_additions() -> None:
    price = EmbeddingPrice(usd_per_million_tokens=2.0, label="test quote")
    result = measure_churn(
        "alpha beta|repeat words|repeat words",
        "alpha beta|repeat words|new token phrase",
        chunker=PipeChunker(),
        strategy="pipe",
        operation=EditOperation.REPLACE_SAME_LENGTH,
        price=price,
    )

    assert result.original_chunk_count == 3
    assert result.revised_chunk_count == 3
    assert result.reused_chunk_count == 2
    assert result.chunks_to_embed == 1
    assert result.chunks_removed == 1
    assert result.tokens_to_embed == 3
    assert result.reembed_fraction == pytest.approx(1 / 3)
    assert result.estimated_cost_usd == pytest.approx(0.000006)
    assert result.price.label == "test quote"


def test_multiset_does_not_reuse_one_old_duplicate_twice() -> None:
    result = measure_churn(
        "same",
        "same|same",
        chunker=PipeChunker(),
        strategy="pipe",
        operation=EditOperation.APPEND,
    )
    assert result.reused_chunk_count == 1
    assert result.chunks_to_embed == 1
    assert result.reembed_fraction == 0.5


def test_reordering_preserves_multiset_reuse() -> None:
    result = measure_churn(
        "first section|second section",
        "second section|first section",
        chunker=PipeChunker(),
        strategy="pipe",
        operation=EditOperation.REORDER_SECTIONS,
    )
    assert result.reused_chunk_count == 2
    assert result.chunks_to_embed == 0
    assert result.chunks_removed == 0
    assert result.reembed_fraction == 0.0


def test_empty_revision_has_zero_fraction_and_reports_removal() -> None:
    result = measure_churn(
        "one|two",
        "",
        chunker=PipeChunker(),
        strategy="pipe",
        operation=EditOperation.DELETE_PARAGRAPH,
    )
    assert result.revised_chunk_count == 0
    assert result.reembed_fraction == 0.0
    assert result.chunks_removed == 2


def test_snapshot_prefers_explicit_chunk_shape() -> None:
    snapshot = snapshot_chunks([ShapedChunk("two words", "stable-hash", 9)])[0]
    assert snapshot.text == "two words"
    assert snapshot.chunk_hash == "stable-hash"
    assert snapshot.token_count == 9


def test_benchmark_shape_and_fixture_notice() -> None:
    summary = benchmark_churn(
        strategies={"pipe": PipeChunker()},
        corpora=[get_corpus("field-guide")],
        operations=[EditOperation.APPEND, EditOperation.INSERT_SENTENCE],
    )
    assert len(summary.results) == 2
    assert {result.operation for result in summary.results} == {
        EditOperation.APPEND,
        EditOperation.INSERT_SENTENCE,
    }
    assert "versioned regression data" in summary.fixture_notice
    assert len(summary.summary_rows()) == 2
    json.dumps(summary.as_dict())


def test_corpus_churn_counts_unchanged_sibling_documents() -> None:
    result = measure_corpus_churn(
        get_corpus("quartz-docs"),
        chunker=PipeChunker(),
        strategy="whole-document",
        operation=EditOperation.APPEND,
    )
    assert result.original_chunk_count == 3
    assert result.revised_chunk_count == 3
    assert result.reused_chunk_count == 2
    assert result.chunks_to_embed == 1
    assert result.reembed_fraction == pytest.approx(1 / 3)


def test_price_validation() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        EmbeddingPrice(-1)


def test_default_five_way_churn_regression() -> None:
    summary = benchmark_churn(
        corpora=[get_corpus("field-guide")],
        operations=[EditOperation.INSERT_SENTENCE],
    )
    assert tuple(result.strategy for result in summary.results) == DEFAULT_STRATEGY_NAMES
    by_strategy = {result.strategy: result for result in summary.results}
    assert by_strategy["fixed"].reembed_fraction >= 0.9
    assert by_strategy["cdc-rabin"].reembed_fraction <= 0.25
    assert by_strategy["cdc-rabin+snap"].reembed_fraction <= 0.25
    assert by_strategy["cdc-rabin"].chunks_to_embed < by_strategy["fixed"].chunks_to_embed


def test_full_builtin_churn_regression_threshold() -> None:
    summary = benchmark_churn()
    by_strategy = {
        strategy: [result for result in summary.results if result.strategy == strategy]
        for strategy in DEFAULT_STRATEGY_NAMES
    }

    def weighted_fraction(strategy: str) -> float:
        results = by_strategy[strategy]
        return sum(result.chunks_to_embed for result in results) / sum(
            result.revised_chunk_count for result in results
        )

    assert len(summary.results) == 225
    assert weighted_fraction("cdc-rabin") <= 0.35
    assert weighted_fraction("cdc-rabin+snap") <= 0.35
    assert weighted_fraction("cdc-rabin") < weighted_fraction("fixed")
