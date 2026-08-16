"""Deterministic normalized word streams with original-source offsets."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import Literal, overload

from steadlith._legacy_wire import V1_NORMALIZER

NORMALIZER_VERSION = V1_NORMALIZER
DEFAULT_TOKENIZER_ID = "word-v1"
PARAGRAPH_MARKER = "\n\n"

TokenCounter = Callable[[str], int]

_WORD_RE = re.compile(r"\S+", re.UNICODE)
_PARAGRAPH_RE = re.compile(r"\n[\t\f\v ]*\n")
_SENTENCE_END_RE = re.compile(r"[.!?](?:[\"'\)\]\}]+)?$")


def default_token_count(word: str) -> int:
    """Return Steadlith's model-independent v1 token estimate (one per word)."""

    del word
    return 1


def resolve_tokenizer_id(
    token_counter: TokenCounter | None, tokenizer_id: str | None = None
) -> str:
    """Return a truthful identity for ``token_counter`` or reject ambiguity.

    ``word-v1`` is reserved for Steadlith's built-in one-token-per-word counter.
    Custom counters affect chunk boundaries and therefore require a distinct,
    explicit, versioned identity.
    """

    uses_default_counter = token_counter is None or token_counter is default_token_count
    if uses_default_counter:
        if tokenizer_id is None or tokenizer_id == DEFAULT_TOKENIZER_ID:
            return DEFAULT_TOKENIZER_ID
        raise ValueError(f"tokenizer_id {tokenizer_id!r} requires a matching custom token_counter")
    if not tokenizer_id:
        raise ValueError("a custom token_counter requires an explicit tokenizer_id")
    if tokenizer_id == DEFAULT_TOKENIZER_ID:
        raise ValueError(
            "a custom token_counter requires an explicit tokenizer_id distinct from "
            "the default; "
            f"{DEFAULT_TOKENIZER_ID!r} is reserved for Steadlith's default token counter"
        )
    return tokenizer_id


@dataclass(frozen=True)
class NormalizedWord:
    text: str
    start_offset: int
    end_offset: int
    token_count: int
    cumulative_tokens: int
    paragraph_before: bool = False


@dataclass(frozen=True)
class StreamItem:
    """An explicit word or paragraph-marker view of a normalized stream."""

    kind: Literal["word", "paragraph_break"]
    text: str
    start_offset: int
    end_offset: int
    word_index: int


@dataclass(frozen=True)
class NormalizedStream(Sequence[NormalizedWord]):
    source: str
    words: tuple[NormalizedWord, ...]
    paragraph_breaks: frozenset[int]
    token_prefix: tuple[int, ...]
    normalizer_version: str = NORMALIZER_VERSION
    tokenizer_id: str = DEFAULT_TOKENIZER_ID

    def __len__(self) -> int:
        return len(self.words)

    def __iter__(self) -> Iterator[NormalizedWord]:
        return iter(self.words)

    @overload
    def __getitem__(self, index: int) -> NormalizedWord: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[NormalizedWord]: ...

    def __getitem__(self, index: int | slice) -> NormalizedWord | Sequence[NormalizedWord]:
        return self.words[index]

    @property
    def word_count(self) -> int:
        return len(self.words)

    @property
    def token_count(self) -> int:
        return self.token_prefix[-1]

    @property
    def text(self) -> str:
        return self.text_between(0, len(self.words))

    @property
    def items(self) -> tuple[StreamItem, ...]:
        result: list[StreamItem] = []
        previous_end = self.words[0].start_offset if self.words else 0
        for index, word in enumerate(self.words):
            if word.paragraph_before:
                result.append(
                    StreamItem(
                        "paragraph_break", PARAGRAPH_MARKER, previous_end, word.start_offset, index
                    )
                )
            result.append(StreamItem("word", word.text, word.start_offset, word.end_offset, index))
            previous_end = word.end_offset
        return tuple(result)

    def tokens_between(self, start: int, end: int) -> int:
        self._validate_slice(start, end)
        return self.token_prefix[end] - self.token_prefix[start]

    def text_between(self, start: int, end: int) -> str:
        self._validate_slice(start, end)
        pieces: list[str] = []
        for index in range(start, end):
            word = self.words[index]
            if pieces:
                pieces.append(PARAGRAPH_MARKER if word.paragraph_before else " ")
            pieces.append(word.text)
        return "".join(pieces)

    def source_offsets(self, start: int, end: int) -> tuple[int, int]:
        self._validate_slice(start, end)
        if start == end:
            if not self.words:
                return (0, 0)
            offset = (
                self.words[start].start_offset
                if start < len(self.words)
                else self.words[-1].end_offset
            )
            return (offset, offset)
        return self.words[start].start_offset, self.words[end - 1].end_offset

    def is_sentence_break(self, position: int) -> bool:
        return 0 < position <= len(self.words) and bool(
            _SENTENCE_END_RE.search(self.words[position - 1].text)
        )

    def is_paragraph_break(self, position: int) -> bool:
        return position in self.paragraph_breaks

    def _validate_slice(self, start: int, end: int) -> None:
        if not 0 <= start <= end <= len(self.words):
            raise IndexError(f"invalid stream slice [{start}:{end}]")


def _contains_paragraph_break(separator: str) -> bool:
    normalized = separator.replace("\r\n", "\n").replace("\r", "\n")
    return bool(_PARAGRAPH_RE.search(normalized))


def normalize_stream(
    text: str,
    token_counter: TokenCounter | None = None,
    *,
    tokenizer_id: str | None = None,
) -> NormalizedStream:
    """Normalize ``text`` and retain half-open character offsets into it.

    Whitespace becomes either a single space or an explicit paragraph marker.
    NFC normalization is applied to each word independently, so offsets always
    continue to refer to the unmodified Python source string.
    """

    resolved_tokenizer_id = resolve_tokenizer_id(token_counter, tokenizer_id)
    count_tokens = token_counter or default_token_count
    words: list[NormalizedWord] = []
    paragraph_breaks: set[int] = set()
    prefix = [0]
    previous_end = 0
    for match in _WORD_RE.finditer(text):
        separator = text[previous_end : match.start()]
        paragraph_before = bool(words) and _contains_paragraph_break(separator)
        if paragraph_before:
            paragraph_breaks.add(len(words))
        normalized_word = unicodedata.normalize("NFC", match.group(0))
        token_count = count_tokens(normalized_word)
        if isinstance(token_count, bool) or not isinstance(token_count, int):
            raise TypeError("token_counter must return an integer")
        if token_count < 1:
            raise ValueError("token_counter must return a positive count for every word")
        prefix.append(prefix[-1] + token_count)
        words.append(
            NormalizedWord(
                text=normalized_word,
                start_offset=match.start(),
                end_offset=match.end(),
                token_count=token_count,
                cumulative_tokens=prefix[-1],
                paragraph_before=paragraph_before,
            )
        )
        previous_end = match.end()
    return NormalizedStream(
        text,
        tuple(words),
        frozenset(paragraph_breaks),
        tuple(prefix),
        tokenizer_id=resolved_tokenizer_id,
    )


def normalize_text(text: str) -> str:
    return normalize_stream(text).text


build_stream = normalize_stream
