from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any

import pytest

from cairn_rag.measure.churn import DEFAULT_STRATEGY_NAMES
from cairn_rag.measure.corpora import (
    BenchmarkDocument,
    CorpusFixture,
    CorpusKind,
    GoldQuestion,
    get_corpus,
)
from cairn_rag.measure.retrieval import (
    ScoringMethod,
    benchmark_retrieval,
    evaluate_retrieval,
    hash_embedding_scores,
    lexical_scores,
    ndcg_at_k,
    recall_at_k,
)


class ParagraphChunker:
    def split(self, text: str, metadata: Mapping[str, Any] | None = None) -> list[str]:
        del metadata
        return [paragraph for paragraph in text.split("\n\n") if paragraph]


def _fixture() -> tuple[CorpusFixture, GoldQuestion]:
    corpus = CorpusFixture(
        name="test-corpus",
        kind=CorpusKind.TECHNICAL_MANUAL,
        description="Metric fixture",
        documents=(
            BenchmarkDocument(
                "guide",
                "Guide",
                (
                    "The red pump starts at eighteen kilopascals.\n\n"
                    "The blue valve is inspected every Friday.\n\n"
                    "A cedar box contains the spare wrench."
                ),
            ),
        ),
    )
    question = GoldQuestion(
        "pump-pressure",
        corpus.name,
        "At what pressure does the red pump start?",
        ("eighteen kilopascals",),
    )
    return corpus, question


def test_metric_functions_use_rank_order() -> None:
    relevance = [True, False, True, False]
    assert recall_at_k(relevance, 2) == 0.5
    assert recall_at_k(relevance, 4) == 1.0
    assert ndcg_at_k([1, 1, 0], 3) == 1.0
    assert ndcg_at_k([1, 0, 1], 3) < 1.0
    assert ndcg_at_k([0, 0], 10) == 0.0
    with pytest.raises(ValueError, match="positive"):
        recall_at_k(relevance, 0)


def test_lexical_scores_are_deterministic_and_rank_overlap() -> None:
    texts = ["red pump pressure", "blue valve schedule", "cedar wrench box"]
    first = lexical_scores("red pump pressure", texts)
    second = lexical_scores("red pump pressure", texts)
    assert first == second
    assert first[0] > first[1]
    assert all(math.isfinite(score) for score in first)


def test_hash_embedding_scores_are_offline_and_deterministic() -> None:
    texts = ["red pump pressure", "blue valve schedule"]
    first = hash_embedding_scores("red pump", texts)
    second = hash_embedding_scores("red pump", texts)
    assert first == second
    assert first[0] > first[1]


@pytest.mark.parametrize("method", list(ScoringMethod))
def test_evaluate_retrieval_finds_gold_evidence(method: ScoringMethod) -> None:
    corpus, question = _fixture()
    result = evaluate_retrieval(
        strategy="paragraph",
        chunker=ParagraphChunker(),
        corpora=[corpus],
        questions=[question],
        k=1,
        scoring_method=method,
    )
    assert result.question_count == 1
    assert result.mean_recall_at_k == 1.0
    assert result.mean_ndcg_at_10 == 1.0
    assert result.question_results[0].top_chunks[0].relevant


def test_benchmark_compares_supplied_strategies() -> None:
    corpus, question = _fixture()
    summary = benchmark_retrieval(
        strategies={"paragraph-a": ParagraphChunker(), "paragraph-b": ParagraphChunker()},
        corpora=[corpus],
        questions=[question],
        k=1,
    )
    assert [result.strategy for result in summary.results] == [
        "paragraph-a",
        "paragraph-b",
    ]
    assert "not published real-corpus results" in summary.fixture_notice
    assert summary.summary_rows()[0]["questions"] == 1
    json.dumps(summary.as_dict())


def test_default_questions_follow_a_filtered_builtin_corpus() -> None:
    summary = benchmark_retrieval(
        strategies={"paragraph": ParagraphChunker()},
        corpora=[get_corpus("field-guide")],
    )
    assert summary.results[0].question_count == 2
    assert {question.corpus_name for question in summary.results[0].question_results} == {
        "field-guide"
    }


def test_default_five_way_retrieval_regression() -> None:
    summary = benchmark_retrieval()
    assert tuple(result.strategy for result in summary.results) == DEFAULT_STRATEGY_NAMES
    assert all(result.question_count == 8 for result in summary.results)
    assert all(result.mean_recall_at_k >= 0.8 for result in summary.results)
    assert all(result.mean_ndcg_at_10 >= 0.75 for result in summary.results)
