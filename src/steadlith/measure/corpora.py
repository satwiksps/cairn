"""Small, deterministic fixtures used by Steadlith's offline benchmarks.

These fixtures are deliberately representative rather than comprehensive.  They
exercise prose, many-file documentation, legal language, source code, and wiki
style text while remaining fast enough for every CI run. Published results apply
to these fixtures; they do not predict every private corpus or embedding model.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum


class CorpusKind(str, Enum):
    """The representative source shape modeled by a fixture."""

    TECHNICAL_MANUAL = "technical-manual"
    DOCUMENTATION_SITE = "documentation-site"
    LEGAL_CORPUS = "legal-corpus"
    CODE_REPOSITORY = "code-repository"
    WIKI_DUMP = "wiki-dump"


class EditOperation(str, Enum):
    """Synthetic edit operations supported by the churn benchmark."""

    INSERT_SENTENCE = "insert-sentence"
    INSERT_PARAGRAPH = "insert-paragraph"
    INSERT_SECTION = "insert-section"
    DELETE_SENTENCE = "delete-sentence"
    DELETE_PARAGRAPH = "delete-paragraph"
    REPLACE_SAME_LENGTH = "replace-same-length"
    REORDER_SECTIONS = "reorder-sections"
    APPEND = "append"
    GLOBAL_REPLACE = "global-replace"


@dataclass(frozen=True)
class BenchmarkDocument:
    """One source document in a benchmark corpus."""

    document_id: str
    title: str
    text: str

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise ValueError("document_id must not be empty")
        if not self.text.strip():
            raise ValueError("benchmark document text must not be empty")


@dataclass(frozen=True)
class CorpusFixture:
    """A deterministic, lightweight corpus fixture."""

    name: str
    kind: CorpusKind
    description: str
    documents: tuple[BenchmarkDocument, ...]

    def __post_init__(self) -> None:
        if not self.documents:
            raise ValueError("a corpus fixture must contain at least one document")
        ids = [document.document_id for document in self.documents]
        if len(ids) != len(set(ids)):
            raise ValueError("document_id values must be unique within a corpus")

    def document(self, document_id: str) -> BenchmarkDocument:
        """Return a document by stable id."""

        for document in self.documents:
            if document.document_id == document_id:
                return document
        raise KeyError(document_id)


@dataclass(frozen=True)
class GoldQuestion:
    """A retrieval question with one or more exact evidence passages.

    Evidence is expressed as a substring instead of a precomputed chunk id,
    because chunk ids necessarily vary by strategy.
    """

    question_id: str
    corpus_name: str
    query: str
    evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.evidence or any(not item for item in self.evidence):
            raise ValueError("a gold question must have non-empty evidence")


@dataclass(frozen=True)
class EditCase:
    """An original/revised document pair for one controlled operation."""

    operation: EditOperation
    document_id: str
    original: str
    revised: str

    def __post_init__(self) -> None:
        if self.original == self.revised:
            raise ValueError(f"{self.operation.value} did not modify the document")
        if self.operation is EditOperation.REPLACE_SAME_LENGTH and len(self.original) != len(
            self.revised
        ):
            raise ValueError("same-length replacement changed the document length")


_TECHNICAL_MANUAL = CorpusFixture(
    name="field-guide",
    kind=CorpusKind.TECHNICAL_MANUAL,
    description="A structured operations manual with long, explanatory sections.",
    documents=(
        BenchmarkDocument(
            "manual",
            "Steadlith Field Guide",
            """# Steadlith Field Guide

## Startup sequence

Inspect the blue pressure gauge before energizing the pump. The safe startup range is 18 to 22 kilopascals. Open the inlet valve, wait for the amber lamp, and record the initial reading in the shift log. Never bypass the interlock while the chamber is occupied.

## Normal operation

The controller samples temperature once per second and stores a rolling ten minute average. A green status lamp means the circulation loop is healthy. If the average exceeds 74 degrees Celsius, reduce the heater set point and inspect the cooling fan. Operators should compare the display with the mechanical gauge at the start of each shift.

## Filter service

Isolate the pump and close both service valves before opening the filter housing. Replace the filter after 400 operating hours or when differential pressure reaches 30 kilopascals. Write the replacement date on the filter collar. Restore the valves in outlet-then-inlet order to avoid a pressure shock.

## Emergency shutdown

Press and hold the red stop switch for three seconds. The controller closes the fuel valve, opens the vent, and records event code E17. Leave the ventilation fan running for at least five minutes. A supervisor must inspect the chamber before the system is restarted.

## Record keeping

Retain shift logs for twelve months. Each log records the operator, startup pressure, peak temperature, alarms, and maintenance work. Digital copies are stored in the north archive and checked every Friday. Corrections must preserve the original entry and include a reason.
""",
        ),
    ),
)


_DOCUMENTATION_SITE = CorpusFixture(
    name="quartz-docs",
    kind=CorpusKind.DOCUMENTATION_SITE,
    description="Several short documentation pages with repeated product vocabulary.",
    documents=(
        BenchmarkDocument(
            "install",
            "Install Quartz",
            """# Install

Install Quartz with `pip install quartz-kit`. Quartz supports Python 3.10 and newer. Run `quartz doctor` after installation to verify the local configuration.

The default configuration file is `quartz.toml` in the project root. Environment variables beginning with `QUARTZ_` override file values.
""",
        ),
        BenchmarkDocument(
            "commands",
            "Quartz commands",
            """# Commands

`quartz build` creates an immutable bundle in the `dist` directory. `quartz inspect` prints bundle metadata without changing it. Use `quartz clean` only when stale local artifacts must be removed.

Add `--json` to inspect output for automation. Quartz writes diagnostics to standard error so the JSON stream remains valid.
""",
        ),
        BenchmarkDocument(
            "deploy",
            "Deploy Quartz",
            """# Deployment

Upload the immutable bundle before updating the release alias. Quartz verifies the bundle checksum at the destination. A failed checksum leaves the existing alias untouched.

Roll back by pointing the alias at the preceding bundle identifier. Keep the three most recent Quartz bundles for routine recovery.
""",
        ),
    ),
)


_LEGAL_CORPUS = CorpusFixture(
    name="harbor-lease",
    kind=CorpusKind.LEGAL_CORPUS,
    description="A compact agreement with long paragraphs and defined terms.",
    documents=(
        BenchmarkDocument(
            "lease",
            "Harbor Equipment Lease",
            """# Harbor Equipment Lease

## 1. Definitions

“Equipment” means the two electric cargo lifts identified in Schedule A, together with their charging cables and safety barriers. “Business Day” means a day other than Saturday, Sunday, or a public holiday in the State. “Site” means Bay Four of the North Harbor warehouse.

## 2. Term and payment

The Term begins on 1 March and continues for twelve calendar months unless ended earlier under this Agreement. The Lessee shall pay 2,400 credits on the first Business Day of each month. An overdue amount accrues simple interest at two percent per month, but no interest accrues during a documented billing dispute.

## 3. Care of equipment

The Lessee shall keep the Equipment at the Site, perform the daily inspection described in Schedule B, and notify the Lessor promptly of any material fault. The Lessee must not modify, sublease, or move the Equipment without prior written consent. Ordinary wear from permitted use is not damage.

## 4. Termination

Either party may terminate for a material breach that remains uncured ten Business Days after written notice. The Lessor may terminate immediately if the Equipment is used outside the Site or if a safety interlock is deliberately disabled. On termination, the Lessee shall return all access cards within two Business Days.
""",
        ),
    ),
)


_CODE_REPOSITORY = CorpusFixture(
    name="ledger-repository",
    kind=CorpusKind.CODE_REPOSITORY,
    description="Source, tests, and maintainer notes from a small code repository.",
    documents=(
        BenchmarkDocument(
            "ledger.py",
            "Ledger implementation",
            '''"""Append-only integer ledger."""

class Ledger:
    def __init__(self) -> None:
        self._entries: list[int] = []

    def append(self, amount: int) -> None:
        """Append one signed amount to the ledger."""
        self._entries.append(amount)

    def balance(self) -> int:
        """Return the sum of all ledger entries."""
        return sum(self._entries)
''',
        ),
        BenchmarkDocument(
            "test_ledger.py",
            "Ledger tests",
            """from ledger import Ledger

def test_balance_includes_negative_entries() -> None:
    ledger = Ledger()
    ledger.append(12)
    ledger.append(-5)
    assert ledger.balance() == 7

def test_new_ledger_is_empty() -> None:
    assert Ledger().balance() == 0
""",
        ),
        BenchmarkDocument(
            "maintainers.md",
            "Maintainer guide",
            """# Maintainer guide

The ledger is append-only: callers add compensating entries instead of mutating history. Run the complete test suite before tagging a release. Release tags use the `ledger-vMAJOR.MINOR.PATCH` format.

Compatibility changes require a migration note. Every migration note includes a before-and-after example and a rollback command.
""",
        ),
    ),
)


_WIKI_DUMP = CorpusFixture(
    name="island-wiki",
    kind=CorpusKind.WIKI_DUMP,
    description="Short encyclopedia entries with varied factual prose.",
    documents=(
        BenchmarkDocument(
            "glasswing-island",
            "Glasswing Island",
            """# Glasswing Island

Glasswing Island is a volcanic island in the Pelican Sea. Its highest point is Mount Oriel at 812 metres. The permanent settlement, East Haven, grew around a sheltered natural harbour.

The island council established the Oriel Cloud Forest reserve in 1986. Winter petrels nest on the northern cliffs from May through August. Ferries reach East Haven twice each week during winter.
""",
        ),
        BenchmarkDocument(
            "lumen-observatory",
            "Lumen Observatory",
            """# Lumen Observatory

Lumen Observatory opened in 1934 on the dry southern plateau of Glasswing Island. Its primary instrument is a 1.8 metre reflecting telescope named Argo. The observatory catalogued 3,200 variable stars between 1951 and 1972.

Public tours are offered on the first Saturday of each month. Heavy cloud or winds above 60 kilometres per hour cause tours to be cancelled.
""",
        ),
    ),
)


BUILTIN_CORPORA: tuple[CorpusFixture, ...] = (
    _TECHNICAL_MANUAL,
    _DOCUMENTATION_SITE,
    _LEGAL_CORPUS,
    _CODE_REPOSITORY,
    _WIKI_DUMP,
)
"""Representative offline fixtures. They are CI data, not research corpora."""


BUILTIN_GOLD_QUESTIONS: tuple[GoldQuestion, ...] = (
    GoldQuestion(
        "manual-startup-range",
        "field-guide",
        "What pressure range is safe during pump startup?",
        ("18 to 22 kilopascals",),
    ),
    GoldQuestion(
        "manual-filter-hours",
        "field-guide",
        "After how many operating hours should the filter be replaced?",
        ("400 operating hours",),
    ),
    GoldQuestion(
        "docs-config-location",
        "quartz-docs",
        "Where is the default Quartz configuration file?",
        ("`quartz.toml` in the project root",),
    ),
    GoldQuestion(
        "docs-rollback",
        "quartz-docs",
        "How do you roll back a Quartz deployment?",
        ("preceding bundle identifier",),
    ),
    GoldQuestion(
        "lease-cure-period",
        "harbor-lease",
        "How long does a party have to cure a material breach?",
        ("ten Business Days after written notice",),
    ),
    GoldQuestion(
        "repository-tag-format",
        "ledger-repository",
        "What format do ledger release tags use?",
        ("`ledger-vMAJOR.MINOR.PATCH`",),
    ),
    GoldQuestion(
        "wiki-telescope",
        "island-wiki",
        "What is the name of the observatory's reflecting telescope?",
        ("telescope named Argo",),
    ),
    GoldQuestion(
        "wiki-reserve-year",
        "island-wiki",
        "When was the Oriel Cloud Forest reserve established?",
        ("reserve in 1986",),
    ),
)
"""Gold questions for deterministic retrieval regression tests."""


def get_corpus(name: str) -> CorpusFixture:
    """Return a built-in corpus by name."""

    for corpus in BUILTIN_CORPORA:
        if corpus.name == name:
            return corpus
    raise KeyError(name)


def questions_for(corpus_name: str) -> tuple[GoldQuestion, ...]:
    """Return the gold questions for ``corpus_name`` in stable order."""

    return tuple(
        question for question in BUILTIN_GOLD_QUESTIONS if question.corpus_name == corpus_name
    )


_SENTENCE_END_RE = re.compile(r"[.!?](?=\s|$)")
_PARAGRAPH_SEPARATOR_RE = re.compile(r"\r?\n[ \t]*\r?\n")
_HEADING_RE = re.compile(r"(?m)^#{1,6}[ \t]+[^\r\n]+(?:\r?\n)?")
_WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_-]{3,}\b")
_STOP_WORDS = frozenset(
    {
        "after",
        "before",
        "each",
        "from",
        "into",
        "must",
        "only",
        "shall",
        "that",
        "their",
        "then",
        "this",
        "when",
        "with",
    }
)


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    starts = [0]
    ends: list[int] = []
    for match in _SENTENCE_END_RE.finditer(text):
        ends.append(match.end())
        next_start = match.end()
        while next_start < len(text) and text[next_start].isspace():
            next_start += 1
        starts.append(next_start)
    if not ends or ends[-1] < len(text.rstrip()):
        ends.append(len(text.rstrip()))
    spans: list[tuple[int, int]] = []
    for start, end in zip(starts, ends, strict=False):
        while start < end and text[start].isspace():
            start += 1
        if start < end:
            spans.append((start, end))
    return spans


def _paragraph_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    for separator in _PARAGRAPH_SEPARATOR_RE.finditer(text):
        end = separator.start()
        if text[start:end].strip():
            spans.append((start, end))
        start = separator.end()
    if text[start:].strip():
        spans.append((start, len(text)))
    return spans


def _section_spans(text: str) -> list[tuple[int, int]]:
    headings = list(_HEADING_RE.finditer(text))
    if len(headings) < 2:
        return _paragraph_spans(text)
    return [
        (heading.start(), headings[index + 1].start() if index + 1 < len(headings) else len(text))
        for index, heading in enumerate(headings)
    ]


def _body_section_spans(text: str) -> list[tuple[int, int]]:
    """Return reorderable body sections, preserving a level-one title block."""

    sections = _section_spans(text)
    if len(sections) >= 3:
        first_text = text[sections[0][0] : sections[0][1]]
        second_text = text[sections[1][0] : sections[1][1]]
        if first_text.startswith("# ") and second_text.startswith("## "):
            return sections[1:]
    return sections


def _insert_after(text: str, position: int, addition: str, separator: str) -> str:
    left = text[:position].rstrip()
    right = text[position:].lstrip()
    return left + separator + addition.strip() + (separator if right else "") + right


def _delete_sentence_span(text: str, span: tuple[int, int]) -> str:
    start, end = span
    left = text[:start].rstrip()
    right = text[end:].lstrip()
    separator = " " if left and right else ""
    revised = left + separator + right
    return revised.rstrip() + ("\n" if text.endswith("\n") else "")


def _delete_paragraph_span(text: str, span: tuple[int, int]) -> str:
    start, end = span
    revised = text[:start].rstrip() + "\n\n" + text[end:].lstrip()
    return revised.strip() + ("\n" if text.endswith("\n") else "")


def _same_length_replacement(text: str) -> str:
    # Prefer changing body prose rather than a leading heading.  A one-codepoint
    # substitution gives an exact length guarantee for arbitrary fixture text.
    start = min(len(text) - 1, max(0, len(text) // 3))
    for index in list(range(start, len(text))) + list(range(0, start)):
        character = text[index]
        if "a" <= character <= "y" or "A" <= character <= "Y":
            replacement = chr(ord(character) + 1)
            return text[:index] + replacement + text[index + 1 :]
        if character in {"z", "Z"}:
            replacement = "a" if character == "z" else "A"
            return text[:index] + replacement + text[index + 1 :]
    raise ValueError("same-length replacement needs at least one ASCII letter")


def _default_global_term(text: str) -> str:
    counts: dict[str, int] = {}
    spellings: dict[str, str] = {}
    for match in _WORD_RE.finditer(text):
        spelling = match.group(0)
        normalized = spelling.casefold()
        if normalized in _STOP_WORDS:
            continue
        counts[normalized] = counts.get(normalized, 0) + 1
        spellings.setdefault(normalized, spelling)
    repeated = [term for term, count in counts.items() if count > 1]
    if not repeated:
        raise ValueError("global replacement needs a repeated word or an explicit find value")
    chosen = min(repeated, key=lambda term: (-counts[term], term))
    return spellings[chosen]


def apply_edit(
    text: str,
    operation: EditOperation | str,
    *,
    find: str | None = None,
    replacement: str | None = None,
) -> str:
    """Apply one deterministic synthetic edit to ``text``.

    ``find`` and ``replacement`` customize :attr:`EditOperation.GLOBAL_REPLACE`.
    All other inserted content is fixed so benchmark runs are reproducible.
    """

    if not text:
        raise ValueError("text must not be empty")
    operation = EditOperation(operation)

    if operation is EditOperation.INSERT_SENTENCE:
        sentences = _sentence_spans(text)
        if not sentences:
            raise ValueError("sentence insertion needs sentence-like text")
        return _insert_after(
            text,
            sentences[0][1],
            "The calibrated inspection marker was recorded for this benchmark.",
            " ",
        )

    if operation is EditOperation.INSERT_PARAGRAPH:
        paragraphs = _paragraph_spans(text)
        return _insert_after(
            text,
            paragraphs[min(1, len(paragraphs) - 1)][1],
            (
                "Benchmark note: the operator verified the local reading twice. "
                "This inserted paragraph models a focused documentation update."
            ),
            "\n\n",
        )

    if operation is EditOperation.INSERT_SECTION:
        sections = _body_section_spans(text)
        position = sections[0][1]
        return _insert_after(
            text,
            position,
            (
                "## Benchmark amendment\n\n"
                "This added section records a deterministic fixture amendment. "
                "It is intentionally short enough for continuous integration."
            ),
            "\n\n",
        )

    if operation is EditOperation.DELETE_SENTENCE:
        sentences = _sentence_spans(text)
        if len(sentences) < 2:
            raise ValueError("sentence deletion needs at least two sentences")
        return _delete_sentence_span(text, sentences[1])

    if operation is EditOperation.DELETE_PARAGRAPH:
        paragraphs = _paragraph_spans(text)
        if len(paragraphs) < 2:
            raise ValueError("paragraph deletion needs at least two paragraphs")
        return _delete_paragraph_span(text, paragraphs[1])

    if operation is EditOperation.REPLACE_SAME_LENGTH:
        return _same_length_replacement(text)

    if operation is EditOperation.REORDER_SECTIONS:
        sections = _body_section_spans(text)
        if len(sections) < 2:
            raise ValueError("section reordering needs at least two sections")
        first, second = sections[0], sections[1]
        prefix = text[: first[0]]
        first_text = text[first[0] : first[1]].rstrip()
        second_text = text[second[0] : second[1]].rstrip()
        suffix = text[second[1] :]
        return prefix + second_text + "\n\n" + first_text + "\n\n" + suffix.lstrip()

    if operation is EditOperation.APPEND:
        return text.rstrip() + (
            "\n\n## Revision note\n\n"
            "The deterministic benchmark revision was appended after the existing content.\n"
        )

    if operation is EditOperation.GLOBAL_REPLACE:
        term = find or _default_global_term(text)
        if not term:
            raise ValueError("find must not be empty")
        substitute = replacement if replacement is not None else f"{term}-revised"
        if substitute == term:
            raise ValueError("replacement must differ from find")
        pattern = re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE)
        revised, count = pattern.subn(substitute, text)
        if count == 0:
            raise ValueError(f"find value {term!r} was not present")
        return revised

    raise AssertionError(f"unhandled edit operation: {operation}")


def iter_edit_cases(
    corpus: CorpusFixture,
    *,
    document_id: str | None = None,
) -> Iterator[EditCase]:
    """Yield every edit operation against one stable document in ``corpus``.

    By default the longest document is selected, with ``document_id`` used as a
    stable tie-breaker.  This keeps multi-file corpus churn meaningful without
    making the CI fixture large.
    """

    if document_id is None:
        candidates = sorted(corpus.documents, key=lambda item: (-len(item.text), item.document_id))
    else:
        candidates = [corpus.document(document_id)]

    selected: BenchmarkDocument | None = None
    revisions: dict[EditOperation, str] = {}
    last_error: ValueError | None = None
    for candidate in candidates:
        try:
            candidate_revisions = {
                operation: apply_edit(candidate.text, operation) for operation in EditOperation
            }
        except ValueError as error:
            last_error = error
            continue
        selected = candidate
        revisions = candidate_revisions
        break
    if selected is None:
        if last_error is not None:
            raise ValueError(
                f"corpus {corpus.name!r} has no document supporting all edit operations"
            ) from last_error
        raise ValueError(f"corpus {corpus.name!r} has no documents")
    for operation in EditOperation:
        yield EditCase(operation, selected.document_id, selected.text, revisions[operation])


def validate_fixtures() -> None:
    """Validate evidence and edit invariants; useful in downstream test suites."""

    corpus_names = {corpus.name for corpus in BUILTIN_CORPORA}
    for question in BUILTIN_GOLD_QUESTIONS:
        if question.corpus_name not in corpus_names:
            raise ValueError(f"unknown gold corpus: {question.corpus_name}")
        haystack = "\n".join(
            document.text for document in get_corpus(question.corpus_name).documents
        )
        for passage in question.evidence:
            if passage not in haystack:
                raise ValueError(f"missing evidence for {question.question_id}: {passage!r}")
    for corpus in BUILTIN_CORPORA:
        for case in iter_edit_cases(corpus):
            if case.operation is EditOperation.REPLACE_SAME_LENGTH:
                assert len(case.original) == len(case.revised)


__all__ = [
    "BUILTIN_CORPORA",
    "BUILTIN_GOLD_QUESTIONS",
    "BenchmarkDocument",
    "CorpusFixture",
    "CorpusKind",
    "EditCase",
    "EditOperation",
    "GoldQuestion",
    "apply_edit",
    "get_corpus",
    "iter_edit_cases",
    "questions_for",
    "validate_fixtures",
]
