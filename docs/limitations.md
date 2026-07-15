# Limitations and risk register

Cairn is experimental software. This page distinguishes measured behavior from design intent and should be read before production evaluation.

## No published performance or retrieval result yet

The project's motivating churn numbers are targets for a benchmark, not established results. There is not yet a published, reproducible comparison across the proposed corpora, edit patterns, chunkers, and embedding models.

Content-defined chunks may retrieve worse than semantic or structure-aware chunks. No cost reduction compensates for a material quality regression. Evaluate recall, nDCG, answer quality, latency, and churn on representative private data before choosing a strategy.

## Best-case workload is specific

Cairn is designed for large documents with edits that are small relative to the source. It is less useful when documents are short, regenerated wholesale, heavily normalized upstream, or replaced under new identifiers. Global find-and-replace can legitimately invalidate most chunks.

## Boundary quality is not semantic quality

Plain Rabin CDC reacts to content patterns, not meaning. Boundaries can fall inside sentences or separate tightly related passages. Optional local snapping may improve readability, but it can also change size distributions and has not yet established a retrieval benefit.

The dependency-free `SemanticChunker` defaults to lexical Jaccard similarity. Built-in benchmark tables label it `semantic-lexical-proxy`; it is a deterministic structural baseline, not an embedding-based semantic result. A real semantic comparison must inject and identify an embedding similarity function.

Structure-aware Markdown, HTML, code, tables, figures, and PDFs are unsupported because they require format-specific extraction and boundary handling. The text algorithm does not imply those capabilities.

## Stateful fallback boundaries reduce practical locality

The rolling fingerprint candidates are local, but the current `tttd-v1` segmentation rule also measures minimum and maximum sizes from the preceding emitted boundary. Maximum-size hard cuts can therefore reintroduce downstream drift. Choosing the most recent backup candidate does not remove the state dependency: two runs can remain in different backup-boundary phases beyond the proposed fixed locality margin even when neither run reports a hard cut. A later common primary boundary often resynchronizes ordinary inputs, but the current algorithm provides no fixed-distance guarantee.

Hard-cut rate and measured churn must remain visible in `cairn-rag status` and benchmark reports, but a low hard-cut rate is diagnostic evidence rather than proof of locality. The fixed-margin formula in the algorithm document is an acceptance criterion for any strategy that claims strict locality, not a guarantee of the bundled strategy.

Adversarial or highly repetitive input can produce unusual Rabin boundary distributions. Do not assume an average target is a strict bound beyond the configured minimum/maximum enforcement.

## Normalization and token accounting are compatibility inputs

Whitespace normalization intentionally treats some source representations as equivalent. Callers that require exact byte-level distinctions must retain and validate the original source separately.

Tokenizer-independent word boundaries do not remove tokenization concerns: chunk limits still rely on a deterministic token count or estimate. A model may count differently, so providers must validate their actual input limit. Changing normalization, token counting, or boundary parameters changes chunk identity and can cause a broad migration.

The identity schema is not frozen before 1.0.

## Snapping requires additional review

Sentence/paragraph snapping is disabled by default. Patent grants address word-aware CDC and content-defined boundary identification. Before distributing or enabling a snapping implementation, undertake appropriate project-specific patent review. This note identifies a risk; it is not legal advice or a conclusion about infringement, validity, enforceability, current status, or geographic scope.

Non-exhaustive starting points identified during project planning include U.S. Patent Nos. [11,928,092](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11928092), [12,265,513](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12265513), and [10,496,313](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10496313). A qualified review must consider current status, claims, jurisdictions, implementation details, and additional prior art; this list is not a clearance search.

## Backend guarantees vary

Tombstone safety depends on metadata filtering, transaction/isolation behavior, and query-path discipline. Adapters without reliable filtering can only offer degraded physical deletion. A process crash, concurrent writer, or backend consistency delay may require reconciliation before a manifest can be trusted.

An adapter is unsupported until it passes the shared conformance suite against the backend versions it declares. Marketing support is not a substitute for those tests.

The bundled SQLite adapter uses one database file for one logical index. Collection namespaces, staged alias swaps, zero-downtime traffic switching, and timed rollback are not implemented; configuration keys that would imply those capabilities are rejected.

The local migration workflow provides explicit preview/apply, durable config persistence, crash recovery, receipts, and a checked immediate rollback. Rollback is a new SQLite generation, not an alias swap: it requires the index/config to still match the latest receipt and the current sources to reproduce the old corpus root. If sources changed, restore their old revision first. If old cache entries were pruned, rollback can call the configured provider again. Compaction retains receipts but may remove the tombstoned vector evidence they describe.

## Resume limits around paid providers

Completed embedding batches are committed to the local cache before index publication and are reused after a later crash. There is still a narrow window between a provider accepting a request and the cache commit. If the process dies there, a retry may incur duplicate spend. The current provider interface does not claim strict billing idempotency; production adapters need a provider-supported idempotency key to close that window.

## Local demo embeddings are not production retrieval

The deterministic hash embedding provider used by examples and tests, when present, exists only to exercise caching and index plumbing without network access. It is **not suitable for production retrieval**, has no semantic-quality claim, and must not be used to evaluate Cairn's retrieval performance.

## Privacy and provider terms

Documents, manifests, embeddings, and even cache hit patterns may be sensitive. Encrypt and restrict persisted state according to the source-data policy; do not log content or credentials by default.

Redistributing embeddings can violate data licenses, privacy obligations, or provider terms. Any shared cache would need deliberately licensed public data and models whose output terms permit redistribution. “Publicly viewable” does not necessarily mean redistributable.

## Merkle roots are integrity identifiers, not signatures

A matching root demonstrates equality under Cairn's canonical hashing rules. It does not establish who produced a manifest or whether an attacker replaced both the manifest and root. Use signed releases, trusted storage, or a separate signature mechanism where authenticity matters.

## Algorithm research remains open

Chonkers and other bounded content-defined schemes are unimplemented research alternatives. They do not silently replace the documented Rabin strategy: adoption requires independent evaluation and a new chunker identity because the change would invalidate existing comparisons and caches.
