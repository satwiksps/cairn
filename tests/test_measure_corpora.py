from __future__ import annotations

import pytest

from cairn_rag.measure.corpora import (
    BUILTIN_CORPORA,
    BUILTIN_GOLD_QUESTIONS,
    CorpusKind,
    EditOperation,
    apply_edit,
    get_corpus,
    iter_edit_cases,
    questions_for,
    validate_fixtures,
)


def test_builtin_fixtures_cover_representative_shapes() -> None:
    assert {corpus.kind for corpus in BUILTIN_CORPORA} == set(CorpusKind)
    assert len(BUILTIN_CORPORA) == 5
    assert all(corpus.documents for corpus in BUILTIN_CORPORA)


def test_all_edits_are_deterministic_and_change_each_fixture() -> None:
    for corpus in BUILTIN_CORPORA:
        first = tuple(iter_edit_cases(corpus))
        second = tuple(iter_edit_cases(corpus))
        assert first == second
        assert {case.operation for case in first} == set(EditOperation)
        assert all(case.original != case.revised for case in first)
        same_length = next(
            case for case in first if case.operation is EditOperation.REPLACE_SAME_LENGTH
        )
        assert len(same_length.original) == len(same_length.revised)


def test_global_replacement_updates_every_occurrence() -> None:
    original = "Stone paths use stone markers. STONE markers remain visible."
    revised = apply_edit(
        original,
        EditOperation.GLOBAL_REPLACE,
        find="stone",
        replacement="cairn",
    )
    assert "stone" not in revised.casefold()
    assert revised.casefold().count("cairn") == 3


def test_gold_evidence_is_present_and_routed_by_corpus() -> None:
    validate_fixtures()
    assert sum(len(questions_for(corpus.name)) for corpus in BUILTIN_CORPORA) == len(
        BUILTIN_GOLD_QUESTIONS
    )
    assert get_corpus("field-guide").kind is CorpusKind.TECHNICAL_MANUAL
    with pytest.raises(KeyError):
        get_corpus("missing")


def test_edits_reject_empty_or_insufficient_input() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        apply_edit("", EditOperation.APPEND)
    with pytest.raises(ValueError, match="at least two sentences"):
        apply_edit("Only one sentence.", EditOperation.DELETE_SENTENCE)
