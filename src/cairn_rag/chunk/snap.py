"""Bounded-local snapping of raw word boundaries to structural breaks."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from cairn_rag.chunk.stream import NormalizedStream

BoundaryKind = Literal["paragraph", "sentence", "raw"]


@dataclass(frozen=True)
class SnapResult:
    position: int
    kind: BoundaryKind
    snapped: bool


def snap_boundary_details(
    anchor_word_index: int,
    stream: NormalizedStream,
    window_words: int = 24,
    *,
    is_valid: Callable[[int], bool] | None = None,
) -> SnapResult:
    """Return a deterministic structural boundary near ``anchor_word_index``.

    Only positions in the bounded ``anchor +/- window_words`` interval are
    inspected.  Paragraph boundaries outrank sentence boundaries; within the
    selected class the nearest wins and an equal-distance tie goes later.
    """

    if not 0 <= anchor_word_index <= len(stream):
        raise IndexError("anchor_word_index is outside the stream")
    if window_words < 0:
        raise ValueError("window_words cannot be negative")
    valid = is_valid or (lambda position: 0 < position <= len(stream))
    lower = max(1, anchor_word_index - window_words)
    upper = min(len(stream), anchor_word_index + window_words)

    paragraphs = [
        position
        for position in range(lower, upper + 1)
        if stream.is_paragraph_break(position) and valid(position)
    ]
    sentences = [
        position
        for position in range(lower, upper + 1)
        if stream.is_sentence_break(position) and valid(position)
    ]
    candidates: list[int]
    kind: BoundaryKind
    if paragraphs:
        candidates = paragraphs
        kind = "paragraph"
    elif sentences:
        candidates = sentences
        kind = "sentence"
    else:
        return SnapResult(anchor_word_index, "raw", False)
    position = min(
        candidates, key=lambda candidate: (abs(candidate - anchor_word_index), -candidate)
    )
    return SnapResult(position, kind, position != anchor_word_index)


def snap_boundary(
    anchor_word_index: int,
    stream: NormalizedStream,
    window_words: int = 24,
    *,
    is_valid: Callable[[int], bool] | None = None,
) -> int:
    return snap_boundary_details(
        anchor_word_index, stream, window_words, is_valid=is_valid
    ).position
