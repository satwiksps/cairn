from __future__ import annotations

import pytest

from cairn_rag.chunk.snap import snap_boundary_details
from cairn_rag.chunk.stream import NORMALIZER_VERSION, normalize_stream, normalize_text


def test_normalization_collapses_whitespace_and_preserves_paragraphs() -> None:
    source = "  Cafe\u0301\t  has\r\n\r\n  two   paragraphs.  "
    stream = normalize_stream(source)

    assert stream.normalizer_version == NORMALIZER_VERSION
    assert stream.text == "Café has\n\ntwo paragraphs."
    assert stream.paragraph_breaks == frozenset({2})
    assert [item.kind for item in stream.items] == [
        "word",
        "word",
        "paragraph_break",
        "word",
        "word",
    ]
    assert source[stream[0].start_offset : stream[0].end_offset] == "Cafe\u0301"
    assert stream.tokens_between(1, 4) == 3


def test_normalize_text_is_deterministic_across_line_endings() -> None:
    assert normalize_text("one\r\n\r\ntwo") == normalize_text("one\n\ntwo")


def test_token_counter_is_validated_and_offsets_remain_source_offsets() -> None:
    stream = normalize_stream(
        "alpha  beta",
        lambda word: len(word),
        tokenizer_id="unicode-codepoints-v1",
    )
    assert stream.tokenizer_id == "unicode-codepoints-v1"
    assert stream.token_prefix == (0, 5, 9)
    assert stream.source_offsets(0, 2) == (0, 11)
    with pytest.raises(ValueError, match="explicit tokenizer_id"):
        normalize_stream("ambiguous", lambda word: len(word))
    with pytest.raises(ValueError, match="reserved"):
        normalize_stream("ambiguous", lambda word: len(word), tokenizer_id="word-v1")
    with pytest.raises(ValueError, match="positive"):
        normalize_stream("bad", lambda word: 0, tokenizer_id="invalid-counter-v1")


def test_snapping_prefers_paragraph_and_ties_go_later() -> None:
    paragraph_stream = normalize_stream("one ends. three four\n\nfive six. seven")
    result = snap_boundary_details(3, paragraph_stream, 3)
    assert result.position == 4
    assert result.kind == "paragraph"

    sentence_stream = normalize_stream("one. two three. four")
    tied = snap_boundary_details(2, sentence_stream, 2)
    assert tied.position == 3
    assert tied.kind == "sentence"


def test_snapping_respects_bounded_window_and_validity_filter() -> None:
    stream = normalize_stream("one. two three four five. six")
    assert snap_boundary_details(3, stream, 1).position == 3
    assert snap_boundary_details(3, stream, 3, is_valid=lambda position: position < 3).position == 1
