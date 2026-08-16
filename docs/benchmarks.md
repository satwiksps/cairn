# Reproducible benchmark results

These tables are the regression baseline carried into Steadlith 0.3.0. They were generated on 2026-08-16 from the five versioned corpora and eight gold questions bundled with the package.

The corpora represent a technical manual, documentation site, legal agreement, small code repository, and wiki. Churn applies nine deterministic edits to each corpus: sentence, paragraph, and section insertion; sentence and paragraph deletion; same-length replacement; section reorder; append; and global replacement.

## Churn

`Re-embed` is the total number of revised chunks without a matching old hash divided by all revised chunks across 45 corpus/edit cases. Lower is better.

| Strategy | Cases | Chunks to embed | Revised chunks | Re-embed | Tokens to embed |
| --- | ---: | ---: | ---: | ---: | ---: |
| fixed | 45 | 106 | 199 | 53.3% | 4,340 |
| recursive | 45 | 62 | 164 | 37.8% | 2,898 |
| semantic-lexical-proxy | 45 | 94 | 363 | 25.9% | 1,932 |
| cdc-rabin | 45 | 71 | 217 | 32.7% | 2,960 |
| cdc-rabin+snap | 45 | 67 | 212 | 31.6% | 2,720 |

On these fixtures, unsnapped Rabin CDC reduces the weighted re-embed fraction from 53.3% for fixed chunks to 32.7%. The lexical semantic proxy produces smaller chunks and the lowest fraction; it is included as a comparison, not presented as a learned semantic model.

## Retrieval

All strategies answer the same eight exact-evidence questions. Recall is measured at 5 and ranking quality at nDCG@10. The lexical scorer uses deterministic TF-IDF; hash embedding uses the offline unigram/bigram provider used by the starter configuration.

| Strategy | Lexical recall@5 | Lexical nDCG@10 | Hash recall@5 | Hash nDCG@10 |
| --- | ---: | ---: | ---: | ---: |
| fixed | 1.000 | 1.000 | 1.000 | 1.000 |
| recursive | 1.000 | 1.000 | 1.000 | 1.000 |
| semantic-lexical-proxy | 1.000 | 1.000 | 1.000 | 0.908 |
| cdc-rabin | 1.000 | 0.923 | 1.000 | 0.866 |
| cdc-rabin+snap | 1.000 | 1.000 | 1.000 | 0.929 |

The default `cdc-rabin` strategy preserves recall@5 on every bundled question. Its ranking score is lower than fixed chunking on this small fixture, which is why Steadlith reports retrieval alongside churn instead of claiming cost savings alone.

## Reproduce

From an installed release or source checkout:

```bash
steadlith measure churn --json
steadlith measure retrieval --scoring lexical --json
steadlith measure retrieval --scoring hash-embedding --json
```

The full JSON output contains every corpus, edit, question, and retained ranking. CI enforces a maximum 35% weighted re-embed fraction for both CDC strategies, recall@5 of 1.0 for default CDC, lexical nDCG@10 of at least 0.90, and hash nDCG@10 of at least 0.85.

## Interpretation

These results establish deterministic project regressions and an immediately usable offline lexical workflow. They do not establish semantic answer quality for an unrelated corpus. Evaluate the chosen embedding model and questions on representative data before production rollout.
