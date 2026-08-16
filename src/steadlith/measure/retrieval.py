"""Deterministic, offline retrieval-quality regression measurements.

The built-in lexical and feature-hash scorers require no model download or
network access.  They are intended to catch regressions and compare chunking
strategies under identical conditions; they are not substitutes for evaluation
on a user's real corpus and production embedding model.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from steadlith.embed.providers.hash import HashEmbeddingProvider

from .churn import Chunker, default_strategies, split_for_measurement
from .corpora import (
    BUILTIN_CORPORA,
    BUILTIN_GOLD_QUESTIONS,
    CorpusFixture,
    GoldQuestion,
)


class ScoringMethod(str, Enum):
    """Built-in deterministic ranking methods."""

    LEXICAL = "lexical"
    HASH_EMBEDDING = "hash-embedding"


class EmbeddingScorer(Protocol):
    """Subset of the embedding-provider contract used by retrieval evaluation."""

    def embed(self, texts: Sequence[str]) -> list[tuple[float, ...]]: ...


@dataclass(frozen=True)
class RetrievedChunk:
    """One ranked chunk retained for result inspection."""

    document_id: str
    chunk_index: int
    text: str
    score: float
    relevant: bool

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation."""

        return {
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "score": self.score,
            "relevant": self.relevant,
        }


@dataclass(frozen=True)
class QuestionResult:
    """Metrics for one gold question."""

    question_id: str
    corpus_name: str
    query: str
    strategy: str
    scoring_method: ScoringMethod
    relevant_chunk_count: int
    recall_at_k: float
    ndcg_at_10: float
    top_chunks: tuple[RetrievedChunk, ...]

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation suitable for CLI output."""

        return {
            "question_id": self.question_id,
            "corpus_name": self.corpus_name,
            "query": self.query,
            "strategy": self.strategy,
            "scoring_method": self.scoring_method.value,
            "relevant_chunk_count": self.relevant_chunk_count,
            "recall_at_k": self.recall_at_k,
            "ndcg_at_10": self.ndcg_at_10,
            "top_chunks": [chunk.as_dict() for chunk in self.top_chunks],
        }


@dataclass(frozen=True)
class RetrievalResult:
    """Aggregate retrieval metrics for one chunking strategy."""

    strategy: str
    scoring_method: ScoringMethod
    k: int
    question_results: tuple[QuestionResult, ...]

    @property
    def question_count(self) -> int:
        return len(self.question_results)

    @property
    def mean_recall_at_k(self) -> float:
        if not self.question_results:
            return 0.0
        return sum(result.recall_at_k for result in self.question_results) / len(
            self.question_results
        )

    @property
    def mean_ndcg_at_10(self) -> float:
        if not self.question_results:
            return 0.0
        return sum(result.ndcg_at_10 for result in self.question_results) / len(
            self.question_results
        )

    def summary_row(self) -> dict[str, object]:
        """Return compact columns for a table renderer."""

        return {
            "strategy": self.strategy,
            "scoring": self.scoring_method.value,
            "questions": self.question_count,
            f"recall@{self.k}": self.mean_recall_at_k,
            "nDCG@10": self.mean_ndcg_at_10,
        }

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation suitable for CLI output."""

        return {
            "strategy": self.strategy,
            "scoring_method": self.scoring_method.value,
            "k": self.k,
            "question_count": self.question_count,
            "mean_recall_at_k": self.mean_recall_at_k,
            "mean_ndcg_at_10": self.mean_ndcg_at_10,
            "question_results": [result.as_dict() for result in self.question_results],
        }


@dataclass(frozen=True)
class RetrievalSummary:
    """Results for multiple strategies plus an explicit fixture caveat."""

    results: tuple[RetrievalResult, ...]
    fixture_notice: str = (
        "Built-in fixtures are versioned regression data; results apply only to those fixtures."
    )

    def summary_rows(self) -> tuple[dict[str, object], ...]:
        """Return one compact, JSON-safe row per strategy."""

        return tuple(result.summary_row() for result in self.results)

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation suitable for CLI output."""

        return {
            "fixture_notice": self.fixture_notice,
            "results": [result.as_dict() for result in self.results],
        }


@dataclass(frozen=True)
class _IndexedChunk:
    document_id: str
    chunk_index: int
    text: str


_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
_LEXICAL_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "at",
        "be",
        "by",
        "do",
        "does",
        "for",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "to",
        "what",
        "when",
        "where",
        "which",
        "with",
    }
)


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in (match.group(0).casefold() for match in _TOKEN_RE.finditer(text))
        if token not in _LEXICAL_STOP_WORDS
    )


def lexical_scores(query: str, texts: Sequence[str]) -> tuple[float, ...]:
    """Return deterministic TF-IDF cosine scores for ``query`` and ``texts``."""

    if not texts:
        return ()
    tokenized = [_tokens(text) for text in texts]
    document_frequency: Counter[str] = Counter()
    for tokens in tokenized:
        document_frequency.update(set(tokens))
    size = len(texts)

    def idf(token: str) -> float:
        return math.log((size + 1) / (document_frequency[token] + 1)) + 1.0

    def weighted(tokens: Sequence[str]) -> dict[str, float]:
        counts = Counter(tokens)
        return {token: count * idf(token) for token, count in counts.items()}

    query_vector = weighted(_tokens(query))
    query_norm = math.sqrt(sum(value * value for value in query_vector.values()))
    scores: list[float] = []
    for tokens in tokenized:
        document_vector = weighted(tokens)
        document_norm = math.sqrt(sum(value * value for value in document_vector.values()))
        if not query_norm or not document_norm:
            scores.append(0.0)
            continue
        dot = sum(value * document_vector.get(token, 0.0) for token, value in query_vector.items())
        scores.append(dot / (query_norm * document_norm))
    return tuple(scores)


def hash_embedding_scores(
    query: str,
    texts: Sequence[str],
    *,
    provider: EmbeddingScorer | None = None,
) -> tuple[float, ...]:
    """Return cosine scores from the deterministic offline hash embedder."""

    if not texts:
        return ()
    scorer = provider or HashEmbeddingProvider()
    vectors = scorer.embed([query, *texts])
    if len(vectors) != len(texts) + 1:
        raise ValueError("embedding provider returned an unexpected vector count")
    query_vector = vectors[0]
    query_norm = math.sqrt(sum(value * value for value in query_vector))
    scores: list[float] = []
    for vector in vectors[1:]:
        if len(vector) != len(query_vector):
            raise ValueError("embedding provider returned inconsistent dimensions")
        # The built-in provider normalizes vectors.  Computing the full cosine
        # keeps this function correct for any deterministic custom provider.
        vector_norm = math.sqrt(sum(value * value for value in vector))
        if not query_norm or not vector_norm:
            scores.append(0.0)
        else:
            dot = sum(left * right for left, right in zip(query_vector, vector, strict=True))
            scores.append(dot / (query_norm * vector_norm))
    return tuple(scores)


def recall_at_k(
    ranked_relevance: Sequence[bool | int | float],
    k: int,
    *,
    total_relevant: int | None = None,
) -> float:
    """Compute recall@``k`` for a ranked relevance sequence."""

    if k <= 0:
        raise ValueError("k must be positive")
    if total_relevant is None:
        total_relevant = sum(1 for value in ranked_relevance if value > 0)
    if total_relevant < 0:
        raise ValueError("total_relevant must be non-negative")
    if total_relevant == 0:
        return 0.0
    retrieved = sum(1 for value in ranked_relevance[:k] if value > 0)
    return min(1.0, retrieved / total_relevant)


def ndcg_at_k(ranked_relevance: Sequence[bool | int | float], k: int = 10) -> float:
    """Compute normalized discounted cumulative gain at ``k``."""

    if k <= 0:
        raise ValueError("k must be positive")
    relevance = [float(value) for value in ranked_relevance]
    if any(value < 0 for value in relevance):
        raise ValueError("relevance values must be non-negative")

    def dcg(values: Sequence[float]) -> float:
        total = 0.0
        for rank, value in enumerate(values[:k]):
            total += (2.0**value - 1.0) / math.log2(rank + 2)
        return total

    ideal = dcg(sorted(relevance, reverse=True))
    return dcg(relevance) / ideal if ideal else 0.0


def ndcg_at_10(ranked_relevance: Sequence[bool | int | float]) -> float:
    """Compute nDCG@10 with an explicit metric-name spelling."""

    return ndcg_at_k(ranked_relevance, 10)


def _is_relevant(text: str, evidence: Sequence[str]) -> bool:
    normalized = " ".join(text.casefold().split())
    return any(" ".join(passage.casefold().split()) in normalized for passage in evidence)


def _index_corpus(corpus: CorpusFixture, chunker: Chunker) -> tuple[_IndexedChunk, ...]:
    chunks: list[_IndexedChunk] = []
    for document in corpus.documents:
        snapshots = split_for_measurement(chunker, document.text)
        chunks.extend(
            _IndexedChunk(document.document_id, index, snapshot.text)
            for index, snapshot in enumerate(snapshots)
        )
    return tuple(chunks)


def evaluate_retrieval(
    *,
    strategy: str,
    chunker: Chunker,
    corpora: Iterable[CorpusFixture] = BUILTIN_CORPORA,
    questions: Iterable[GoldQuestion] | None = None,
    k: int = 5,
    scoring_method: ScoringMethod | str = ScoringMethod.LEXICAL,
    embedding_provider: EmbeddingScorer | None = None,
) -> RetrievalResult:
    """Evaluate one strategy against exact-evidence gold questions."""

    if k <= 0:
        raise ValueError("k must be positive")
    if not strategy.strip():
        raise ValueError("strategy must not be empty")
    scoring_method = ScoringMethod(scoring_method)
    corpus_by_name = {corpus.name: corpus for corpus in corpora}
    question_values = (
        tuple(
            question
            for question in BUILTIN_GOLD_QUESTIONS
            if question.corpus_name in corpus_by_name
        )
        if questions is None
        else tuple(questions)
    )
    if not question_values:
        raise ValueError("at least one gold question is required")
    indexed: dict[str, tuple[_IndexedChunk, ...]] = {}
    results: list[QuestionResult] = []

    for question in question_values:
        try:
            corpus = corpus_by_name[question.corpus_name]
        except KeyError as error:
            raise ValueError(
                f"gold question {question.question_id!r} references unknown corpus "
                f"{question.corpus_name!r}"
            ) from error
        if corpus.name not in indexed:
            indexed[corpus.name] = _index_corpus(corpus, chunker)
        chunks = indexed[corpus.name]
        texts = [chunk.text for chunk in chunks]
        if scoring_method is ScoringMethod.LEXICAL:
            scores = lexical_scores(question.query, texts)
        else:
            scores = hash_embedding_scores(question.query, texts, provider=embedding_provider)
        relevant = [_is_relevant(chunk.text, question.evidence) for chunk in chunks]
        relevant_count = sum(relevant)
        if relevant_count == 0:
            raise ValueError(
                f"strategy {strategy!r} produced no chunk containing evidence for "
                f"question {question.question_id!r}"
            )
        order = sorted(
            range(len(chunks)),
            key=lambda index: (
                -scores[index],
                chunks[index].document_id,
                chunks[index].chunk_index,
            ),
        )
        ranked_relevance = [relevant[index] for index in order]
        retained = max(k, 10)
        top_chunks = tuple(
            RetrievedChunk(
                document_id=chunks[index].document_id,
                chunk_index=chunks[index].chunk_index,
                text=chunks[index].text,
                score=scores[index],
                relevant=relevant[index],
            )
            for index in order[:retained]
        )
        results.append(
            QuestionResult(
                question_id=question.question_id,
                corpus_name=question.corpus_name,
                query=question.query,
                strategy=strategy,
                scoring_method=scoring_method,
                relevant_chunk_count=relevant_count,
                recall_at_k=recall_at_k(ranked_relevance, k, total_relevant=relevant_count),
                ndcg_at_10=ndcg_at_10(ranked_relevance),
                top_chunks=top_chunks,
            )
        )
    return RetrievalResult(strategy, scoring_method, k, tuple(results))


def benchmark_retrieval(
    *,
    strategies: Mapping[str, Chunker] | None = None,
    corpora: Iterable[CorpusFixture] = BUILTIN_CORPORA,
    questions: Iterable[GoldQuestion] | None = None,
    k: int = 5,
    scoring_method: ScoringMethod | str = ScoringMethod.LEXICAL,
    embedding_provider: EmbeddingScorer | None = None,
) -> RetrievalSummary:
    """Compare all five built-in strategies on the offline gold fixture."""

    selected = dict(strategies) if strategies is not None else default_strategies()
    if not selected:
        raise ValueError("at least one strategy is required")
    corpus_values = tuple(corpora)
    corpus_names = {corpus.name for corpus in corpus_values}
    question_values = (
        tuple(
            question for question in BUILTIN_GOLD_QUESTIONS if question.corpus_name in corpus_names
        )
        if questions is None
        else tuple(questions)
    )
    results = tuple(
        evaluate_retrieval(
            strategy=name,
            chunker=chunker,
            corpora=corpus_values,
            questions=question_values,
            k=k,
            scoring_method=scoring_method,
            embedding_provider=embedding_provider,
        )
        for name, chunker in selected.items()
    )
    return RetrievalSummary(results)


__all__ = [
    "EmbeddingScorer",
    "QuestionResult",
    "RetrievalResult",
    "RetrievalSummary",
    "RetrievedChunk",
    "ScoringMethod",
    "benchmark_retrieval",
    "evaluate_retrieval",
    "hash_embedding_scores",
    "lexical_scores",
    "ndcg_at_10",
    "ndcg_at_k",
    "recall_at_k",
]
