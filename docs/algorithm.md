# Content-defined chunking algorithm

## Purpose

Steadlith uses content-defined chunking (CDC) so boundary decisions depend on nearby content instead of absolute offsets. The intended result is local change propagation: an edit should alter chunks near the edit without renumbering every downstream boundary.

The current design uses a Rabin-style rolling fingerprint with two-threshold boundary selection. It does **not** use FastCDC: throughput is secondary to a locality property in an indexing pipeline where embedding is normally the expensive operation.

This document describes the implemented algorithm and its acceptance targets. Projected benchmark numbers are not evidence that an implementation satisfies a claimed property.

## 1. Build a normalized word stream

CDC runs over words rather than raw bytes or model tokens:

- byte boundaries can split UTF-8 and ordinary words;
- tokenizer-dependent boundaries would change when an embedding tokenizer changes;
- words provide a stable, model-independent unit.

Normalization is deterministic and versioned. At minimum it normalizes line endings, collapses ordinary whitespace runs, and preserves paragraph boundaries as explicit markers. Every stream item retains source offsets so callers can associate canonical content with the original input.

The normalization version participates in identity. Changing normalization is an explicit migration, not an invisible implementation detail.

Chunk limits are expressed in tokens because model context limits are token-based. Token counting or estimation is supplied as an explicit deterministic function and its identity is covered by chunker parameters. It must not consult a remote service during chunking.

## 2. Compute candidate boundaries

For each eligible word position, maintain a rolling Rabin fingerprint over the previous `window_words` words. A primary candidate occurs when the fingerprint matches the configured primary mask/remainder condition. A weaker backup condition fires more often.

For each chunk under construction:

1. Do not evaluate boundaries below `min_tokens`.
2. Record the most recent backup candidate after the minimum.
3. End the chunk immediately at the first primary candidate after the minimum.
4. If adding content would exceed `max_tokens`, cut at the most recent valid backup candidate.
5. If no backup exists, use a hard cut at the maximum and increment the hard-cut diagnostic.

Conceptually:

```text
for each word position:
    update rolling fingerprint
    update deterministic token count

    if token_count < min_tokens:
        continue

    if matches backup:
        remember this position

    if matches primary:
        emit at this position
    else if token_count reaches max_tokens:
        emit at remembered backup, or hard-cut at the maximum
```

Implementations must handle the final short tail deterministically and must always make forward progress. Parameter validation rejects non-positive windows, `min_tokens > max_tokens`, masks outside the supported fingerprint width, and any setting that can create empty chunks.

## 3. Optional bounded snapping

Raw CDC candidates can land inside sentences. Steadlith defines optional snapping to a paragraph or sentence boundary, but keeps it disabled by default.

When enabled, snapping is a deterministic function of only the raw anchor and a bounded local window of `snap_window_words` on each side:

```text
window = stream[anchor - S : anchor + S]
candidates = paragraph_and_sentence_breaks(window)

if no candidate exists:
    snapped = anchor
else:
    prefer paragraph candidates over sentence candidates
    choose the nearest candidate in the selected class
    break equal-distance ties toward the later candidate
```

Snapping cannot violate minimum/maximum constraints or create an empty chunk. It must not consult a document-wide sentence parse, section outline, model, mutable dictionary, or neighboring chunk decision.

Word-aware CDC and boundary-snapping techniques are addressed by existing patent grants. Contributors must perform appropriate project-specific review before enabling or substantially changing snapping. This repository does not make a legal conclusion about any claim; see [limitations](limitations.md).

## 4. Locality target and current limitation

Let two documents share a contiguous normalized region of length at least:

```text
2 * (max_tokens + window_words + snap_window_words)
```

The proposed acceptance property excludes a margin of:

```text
max_tokens + window_words + snap_window_words
```

at both ends and requires chunks inside the remaining interior to be byte-identical under identical versions and parameters.

The rolling fingerprint candidate at any position is local: it depends only on the bounded word window ending there. The current `tttd-v1` segmentation rule is nevertheless stateful. Eligibility is measured from the preceding emitted boundary, and both the maximum-size trigger and selection of the most recent backup candidate therefore depend on that earlier boundary. An edit can put two runs into different boundary phases until a common primary candidate happens to resynchronize them. The distance to that candidate is not bounded by `max_tokens + window_words + snap_window_words`.

Consequently, the formula above is an acceptance criterion for any replacement algorithm that claims strict locality, not an invariant proved or satisfied by the current implementation. A passing regression records the exact phase-shifted ranges and hash inequality from a deterministic insertion counterexample with backup boundaries and zero hard cuts. Randomized churn tests remain useful empirical evidence, but passing samples must not be presented as a proof. A strategy that claims this bound must use exact stream/token accounting in property tests rather than assuming one word equals one token.

## 5. Chunk identity

A chunk hash commits to every input that can change its canonical content or boundaries:

```text
H(
    identity_schema_version,
    normalizer_version,
    "cdc-rabin",
    hash(canonical_chunker_parameters),
    canonical_chunk_text,
)
```

Serialization is canonical and length-delimited. At a minimum, chunker parameters cover rolling-window size, polynomial/fingerprint definition, primary and backup conditions, token-counting identity, minimum and maximum sizes, snapping mode/window, and boundary-rule version.

The embedding model is intentionally absent. Embedding cache identity adds `embedding_model_id` and `embedding_parameters_hash` outside the chunk hash.

The v1 wire identity remains the stable contract for existing 0.2 data and Steadlith 1.0. Golden-vector tests pin its canonical parameter hash and chunk hash. Any future incompatible normalization, boundary, token-accounting, or serialization change must use a new identity version and an explicit migration; see [compatibility](compatibility.md).

## 6. Diagnostics and acceptance criteria

Every chunking run should expose enough diagnostics to aggregate:

- chunk count and token-size distribution;
- primary, backup, and hard-cut boundary counts;
- hard-cut rate;
- normalization and chunker identity;
- whether snapping was enabled.

An algorithm change is not accepted solely because it lowers churn. It must also preserve determinism and locality, document identity compatibility, and report retrieval quality on the same corpora. Churn and retrieval results belong side by side.

Chonkers-style algorithms are not implemented. Any adoption would require an independent implementation review, comparative tests, and a new chunker identity; the cited design does not automatically supersede Rabin TTTD.

## References

- Michael O. Rabin, *Fingerprinting by Random Polynomials*, Harvard University Center for Research in Computing Technology, Technical Report TR-15-81, 1981.
- Athicha Muthitacharoen, Benjie Chen, and David Mazières, [*A Low-bandwidth Network File System*](https://www.sosp.org/2001/papers/mazieres.pdf), SOSP 2001, [doi:10.1145/502034.502052](https://doi.org/10.1145/502034.502052).
- Benjamin Berger, [*The Chonkers Algorithm: Content-Defined Chunking with Provable Strict Guarantees on Size and Locality*](https://arxiv.org/html/2509.11121v2), arXiv:2509.11121v2, 2025.
