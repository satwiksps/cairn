from __future__ import annotations

import random

import pytest

from cairn_rag.chunk import (
    CDCChunker,
    CDCParams,
    FixedChunker,
    RecursiveChunker,
    SemanticChunker,
    chunk_stream,
    chunker_from_config,
    create_chunker,
)
from cairn_rag.chunk.cdc import rolling_fingerprints
from cairn_rag.chunk.stream import normalize_stream


def _document(count: int, prefix: str = "word") -> str:
    return " ".join(
        f"{prefix}{index}." if index % 17 == 16 else f"{prefix}{index}" for index in range(count)
    )


def test_rolling_hash_matches_recomputation_for_every_window() -> None:
    stream = normalize_stream(_document(100))
    rolling = rolling_fingerprints(stream, 8)
    for end in range(8, len(stream) + 1):
        # The public rolling sequence must be deterministic; compare to the
        # same words normalized as an isolated local window.
        local = normalize_stream(stream.text_between(end - 8, end))
        for value in rolling_fingerprints(local, 8):
            if value is not None:
                expected = value
        assert rolling[end] == expected


def test_rolling_candidates_are_local_after_randomized_insertions() -> None:
    window = 8
    for case in range(40):
        rng = random.Random(case)
        length = rng.randrange(80, 181)
        words = [f"w{index}_{rng.randrange(1 << 31)}" for index in range(length)]
        insertion_at = rng.randrange(12, length - 12)
        insertion_size = rng.randrange(1, 17)
        inserted = [f"inserted_{case}_{index}" for index in range(insertion_size)]
        original = rolling_fingerprints(normalize_stream(" ".join(words)), window)
        edited = rolling_fingerprints(
            normalize_stream(" ".join(words[:insertion_at] + inserted + words[insertion_at:])),
            window,
        )

        for original_end in range(insertion_at + window, len(words) + 1):
            assert original[original_end] == edited[original_end + insertion_size]


def test_cdc_is_deterministic_and_returns_document_compatible_chunks() -> None:
    params = CDCParams(
        window_words=8,
        min_tokens=16,
        max_tokens=48,
        primary_mask_bits=4,
        backup_mask_bits=2,
    )
    source = _document(400)
    first = CDCChunker(params).split(source, {"source": "manual"})
    second = CDCChunker(params).split(source, {"source": "manual"})

    assert [(chunk.page_content, chunk.metadata) for chunk in first] == [
        (chunk.page_content, chunk.metadata) for chunk in second
    ]
    assert all(chunk.page_content and chunk.metadata["source"] == "manual" for chunk in first)
    assert all(chunk.chunk_hash and len(chunk.chunk_hash) == 64 for chunk in first)
    assert all(chunk.token_count <= params.max_tokens for chunk in first)


def test_cdc_identity_has_a_cross_platform_golden_vector() -> None:
    params = CDCParams(
        window_words=4,
        min_tokens=4,
        max_tokens=12,
        primary_mask_bits=3,
        backup_mask_bits=2,
    )
    source = (
        "Alpha  beta.\r\n\r\nGamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron."
    )
    chunks = CDCChunker(params).split(source)

    assert params.params_hash == "628208d899483f8c6023e58e4194e9abf9b452c5365a320822720a5a3752bdbe"
    assert [chunk.chunk_hash for chunk in chunks] == [
        "805918370a685db0e3333a93dcc78a88b6f03a2476c533ab9e6730b4338d4308",
        "0a85ff492ecb40ab422c3957e001f6b8ffc8fede12f20d2e0ce9a499f74d4496",
    ]
    assert [(chunk.start_offset, chunk.end_offset) for chunk in chunks] == [(0, 61), (62, 86)]


def test_custom_token_counter_requires_and_commits_to_an_explicit_identity() -> None:
    def codepoint_count(word: str) -> int:
        return len(word)

    params = CDCParams(
        window_words=2,
        min_tokens=1,
        max_tokens=32,
        primary_mask_bits=2,
        backup_mask_bits=1,
    )
    with pytest.raises(ValueError, match="explicit tokenizer_id"):
        CDCChunker(params, codepoint_count)

    default_chunk = CDCChunker(params).split("alpha beta")[0]
    custom_chunker = CDCChunker(
        params,
        codepoint_count,
        tokenizer_id="unicode-codepoints-v1",
    )
    custom_chunk = custom_chunker.split("alpha beta")[0]

    assert custom_chunk.token_count == 9
    assert custom_chunker.params.tokenizer_id == "unicode-codepoints-v1"
    assert custom_chunk.chunk_hash != default_chunk.chunk_hash
    assert (
        custom_chunk.metadata["chunker_params_hash"]
        != default_chunk.metadata["chunker_params_hash"]
    )

    custom_stream = normalize_stream(
        "alpha beta",
        codepoint_count,
        tokenizer_id="other-codepoint-counter-v1",
    )
    with pytest.raises(ValueError, match="tokenizer identities differ"):
        chunk_stream(custom_stream, custom_chunker.params)


def test_chunkers_reject_an_atomic_word_over_the_token_limit() -> None:
    def five_tokens(_word: str) -> int:
        return 5

    params = CDCParams(
        window_words=2,
        min_tokens=1,
        max_tokens=4,
        primary_mask_bits=2,
        backup_mask_bits=1,
        tokenizer_id="five-per-word-v1",
    )
    with pytest.raises(ValueError, match=r"token count 5.*max_tokens=4"):
        CDCChunker(params, five_tokens).split("oversized")
    with pytest.raises(ValueError, match=r"token count 5.*max_tokens=4"):
        FixedChunker(
            chunk_size_tokens=4,
            token_counter=five_tokens,
            tokenizer_id="five-per-word-v1",
        ).split("oversized")


def test_tttd_counts_primary_backup_and_hard_cut_boundaries() -> None:
    candidate_params = CDCParams(
        window_words=4,
        min_tokens=4,
        max_tokens=12,
        primary_mask_bits=2,
        backup_mask_bits=1,
    )
    candidate_result = CDCChunker(candidate_params).split_with_stats(_document(500, "candidate"))
    assert candidate_result.stats.primary_boundaries > 0
    assert candidate_result.stats.backup_boundaries > 0

    hard_params = CDCParams(
        window_words=4,
        min_tokens=4,
        max_tokens=8,
        primary_mask_bits=63,
        backup_mask_bits=62,
    )
    hard_result = CDCChunker(hard_params).split_with_stats(_document(40, "hard"))
    assert hard_result.stats.hard_cuts == 4
    assert hard_result.stats.hard_cut_rate == 1.0
    assert hard_result.stats.token_counts == (8, 8, 8, 8, 8)


def test_snapping_is_opt_in_and_keeps_size_bounds() -> None:
    raw_params = CDCParams(
        window_words=4,
        min_tokens=8,
        max_tokens=24,
        primary_mask_bits=3,
        backup_mask_bits=2,
        snap_window_words=4,
    )
    snapped_params = raw_params.with_snapping()
    source = " ".join(f"sentence{index}. next{index}" for index in range(100))
    raw = CDCChunker(raw_params).split_with_stats(source)
    snapped = CDCChunker(snapped_params).split_with_stats(source)

    assert not raw_params.snap_to_boundaries
    assert raw.stats.snapped_boundaries == 0
    assert snapped_params.snap_to_boundaries
    assert snapped.stats.snapped_boundaries > 0
    assert all(
        snapped_params.min_tokens <= chunk.token_count <= snapped_params.max_tokens
        for chunk in snapped.chunks[:-1]
    )


def test_semantic_chunker_does_not_split_past_a_structural_unit() -> None:
    source = " ".join(
        [
            "w0",
            "w1",
            "w2",
            "w3",
            "w4",
            "w5",
            "w6",
            "w7",
            "w8.",
            "w9.",
            "w10.",
            "w11",
        ]
    )

    chunks = SemanticChunker(max_tokens=4, min_tokens=1).split(source)

    ranges = [(chunk.metadata["start_word"], chunk.metadata["end_word"]) for chunk in chunks]
    assert ranges == [(0, 4), (4, 8), (8, 9), (9, 10), (10, 11), (11, 12)]
    assert all(chunk.token_count <= 4 for chunk in chunks)


def test_recursive_chunker_separators_drive_boundary_selection() -> None:
    source = "a b. c d e f"

    sentence_chunks = RecursiveChunker(
        max_tokens=4,
        separators=(". ",),
    ).split_text(source)
    unmatched_chunks = RecursiveChunker(
        max_tokens=4,
        separators=("NEVER",),
    ).split_text(source)

    assert sentence_chunks == ["a b.", "c d e f"]
    assert unmatched_chunks == ["a b. c d", "e f"]


def test_chunker_factories_accept_mapping_configuration() -> None:
    cdc = create_chunker("cdc-rabin", params={"max_tokens": 700})
    fixed_params = create_chunker("fixed", params={"chunk_size_tokens": 11})
    fixed = chunker_from_config({"strategy": "fixed", "max_tokens": 7})
    nested = chunker_from_config(
        {"chunker": {"strategy": "recursive", "min_tokens": 2, "max_tokens": 9}}
    )

    assert isinstance(cdc, CDCChunker)
    assert cdc.params.max_tokens == 700
    assert isinstance(fixed_params, FixedChunker)
    assert fixed_params.chunk_size_tokens == 11
    assert isinstance(fixed, FixedChunker)
    assert fixed.chunk_size_tokens == 7
    assert isinstance(nested, RecursiveChunker)
    assert nested.min_tokens == 2
    assert nested.max_tokens == 9
    with pytest.raises(TypeError, match="unknown CDC params"):
        create_chunker("cdc-rabin", params={"max_tokenz": 700})


def test_from_config_rejects_a_path_in_the_pure_chunking_layer() -> None:
    with pytest.raises(TypeError, match="load TOML"):
        CDCChunker.from_config("cairn.toml")


def _locality_case(
    operation: str, seed: int
) -> tuple[list[str], list[str], list[tuple[int, int, int]]]:
    rng = random.Random(seed)
    words = [
        f"token{index}-{rng.randrange(1_000_000)}{'.' if rng.random() < 0.11 else ''}"
        for index in range(2400)
    ]
    edit_start = rng.randrange(180, 320)
    edit_size = rng.randrange(11, 29)
    replacements = [f"edited-{seed}-{index}." for index in range(edit_size)]
    if operation == "insert":
        revised = words[:edit_start] + replacements + words[edit_start:]
        regions = [(edit_start, edit_start + edit_size, len(words) - edit_start)]
    elif operation == "delete":
        revised = words[:edit_start] + words[edit_start + edit_size :]
        regions = [
            (
                edit_start + edit_size,
                edit_start,
                len(words) - edit_start - edit_size,
            )
        ]
    elif operation == "replace":
        revised = words[:edit_start] + replacements + words[edit_start + edit_size :]
        regions = [
            (
                edit_start + edit_size,
                edit_start + edit_size,
                len(words) - edit_start - edit_size,
            )
        ]
    elif operation == "reorder":
        first_size = rng.randrange(310, 360)
        second_size = rng.randrange(310, 360)
        middle = edit_start + first_size
        suffix = middle + second_size
        first = words[edit_start:middle]
        second = words[middle:suffix]
        revised = words[:edit_start] + second + first + words[suffix:]
        regions = [
            (edit_start, edit_start + second_size, first_size),
            (middle, edit_start, second_size),
            (suffix, suffix, len(words) - suffix),
        ]
    else:  # pragma: no cover - guarded by parametrization
        raise AssertionError(operation)
    return words, revised, regions


@pytest.mark.parametrize("operation", ["insert", "delete", "replace", "reorder"])
@pytest.mark.parametrize("seed", [20260815, 8675309])
def test_locality_after_deterministic_random_edits(operation: str, seed: int) -> None:
    words, edited_words, shared_regions = _locality_case(operation, seed)
    params = CDCParams(
        window_words=8,
        min_tokens=16,
        max_tokens=64,
        primary_mask_bits=3,
        backup_mask_bits=1,
        snap_window_words=8,
        snap_to_boundaries=True,
    )
    original_result = CDCChunker(params).split_with_stats(" ".join(words))
    edited_result = CDCChunker(params).split_with_stats(" ".join(edited_words))

    # This fixture exercises examples that do resynchronize.  The explicit
    # counterexample below records that zero hard cuts are not sufficient to prove
    # the proposed fixed-margin locality property for the stateful TTTD rule.
    assert original_result.stats.hard_cuts == 0
    assert edited_result.stats.hard_cuts == 0
    margin = params.max_tokens + params.window_words + params.snap_window_words
    for original_start, edited_start, length in shared_regions:
        if length < 2 * margin:
            continue
        original_interior = [
            chunk.chunk_hash
            for chunk in original_result.chunks
            if chunk.metadata["start_word"] >= original_start + margin
            and chunk.metadata["end_word"] <= original_start + length - margin
        ]
        edited_interior = [
            chunk.chunk_hash
            for chunk in edited_result.chunks
            if chunk.metadata["start_word"] >= edited_start + margin
            and chunk.metadata["end_word"] <= edited_start + length - margin
        ]
        assert original_interior
        assert original_interior == edited_interior


def test_tttd_fixed_margin_locality_counterexample_is_documented() -> None:
    rng = random.Random(35)
    words = [f"w{index}_{rng.randrange(1 << 32):x}" for index in range(60)]
    edit_start = 20
    inserted = [f"X{index}_35" for index in range(7)]
    params = CDCParams(
        window_words=2,
        min_tokens=2,
        max_tokens=8,
        primary_mask_bits=3,
        backup_mask_bits=1,
        snap_window_words=0,
    )

    original = CDCChunker(params).split_with_stats(" ".join(words))
    edited = CDCChunker(params).split_with_stats(
        " ".join(words[:edit_start] + inserted + words[edit_start:])
    )
    assert original.stats.hard_cuts == edited.stats.hard_cuts == 0

    margin = params.max_tokens + params.window_words + params.snap_window_words
    original_interior = [
        chunk
        for chunk in original.chunks
        if chunk.metadata["start_word"] >= edit_start + margin
        and chunk.metadata["end_word"] <= len(words) - margin
    ]
    edited_interior = [
        chunk
        for chunk in edited.chunks
        if chunk.metadata["start_word"] >= edit_start + len(inserted) + margin
        and chunk.metadata["end_word"] <= len(words) + len(inserted) - margin
    ]

    # Original boundaries 33-40 and 40-45 are both inside the proposed
    # interior; after mapping out the insertion, the edited run has 37-45.
    # Assert the counterexample as supported behavior documentation instead of
    # shipping an expected failure that could be mistaken for unfinished work.
    assert [
        (chunk.metadata["start_word"], chunk.metadata["end_word"]) for chunk in original_interior
    ] == [(33, 40), (40, 45)]
    assert [
        (
            chunk.metadata["start_word"] - len(inserted),
            chunk.metadata["end_word"] - len(inserted),
        )
        for chunk in edited_interior
    ] == [(37, 45)]
    assert [chunk.chunk_hash for chunk in original_interior] != [
        chunk.chunk_hash for chunk in edited_interior
    ]


def test_fixed_strategy_demonstrates_offset_boundary_drift() -> None:
    chunker = FixedChunker(chunk_size_tokens=10)
    original = chunker.split(_document(50))
    edited = chunker.split("inserted " + _document(50))
    assert original[1].chunk_hash != edited[1].chunk_hash
