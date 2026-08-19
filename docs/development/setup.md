# Development setup

## Clone and install

```bash
git clone https://github.com/satwiksps/steadlith.git
cd steadlith
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Use one of the optional extras when modifying a provider:

```bash
python -m pip install -e ".[dev,openai]"
python -m pip install -e ".[dev,sentence-transformers]"
```

## Repository layout

```text
src/steadlith/
  chunk/       pure normalization and chunking
  content/     pure hashing, manifests, and Merkle trees
  embed/       provider protocol, batching, and adapters
  index/       planning, source I/O, SQLite adapter, and services
  migrate/     migration preview, receipt, recovery, and rollback
  measure/     deterministic churn and retrieval fixtures
  store/       content-addressed SQLite cache
  cli.py       command parsing and safety gates
docs/          Sphinx and Read the Docs sources
tests/         unit, property, integration-style, and regression tests
website/       separate Next.js landing site
```

## Architectural rules

- `steadlith.chunk` and `steadlith.content` stay deterministic and free of filesystem, environment, network, and configuration lookup.
- Provider SDK imports remain inside optional provider adapters.
- Identity-bearing changes require explicit versioning and golden-vector updates.
- Index publication must remain transactional and stale-writer safe.
- Query paths must exclude tombstones before ranking.
- Source, config, cache import, provider response, and stored-vector inputs remain bounded and validated.
- Behavior changes need tests and user-facing documentation.

## Focus a change

Start from the smallest relevant test file:

```bash
python -m pytest tests/test_cdc_core.py
```

Then run formatting, lint, types, and the full suite before submitting. See [Testing](testing.md).

## Contribution workflow

Read the repository [contribution guide](https://github.com/satwiksps/steadlith/blob/main/CONTRIBUTING.md). For a significant API, identity, migration, or backend change, open an issue before implementation so compatibility and state migration can be agreed first.

Never use private corpora, live secrets, provider responses, or paid embedding vectors as fixtures.
