# Contributing to Cairn

Thank you for improving Cairn. Contributions should be focused, testable, and explicit about compatibility effects.

## Before opening a change

- Search existing issues and pull requests.
- Use a GitHub issue for substantial behavior or API changes before investing in an implementation.
- Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md).
- Do not include private corpora, credentials, API responses, or real embedding data in issues or fixtures.

## Development setup

Cairn supports Python 3.10 and newer.

```bash
git clone https://github.com/satwiksps/cairn.git
cd cairn
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Activate the virtual environment using the command appropriate for your shell. Provider-specific work may also need the `openai` or `sentence-transformers` extra.

The landing site is a separate Next.js application:

```bash
cd website
npm ci
npm run dev
```

## Making changes

- Keep `cairn_rag.chunk` and `cairn_rag.content` deterministic and free of file, environment, and network access.
- Treat changes to normalization, tokenizer identity, chunk parameters, hash inputs, cache keys, manifests, or instance IDs as compatibility changes.
- Preserve transactional visibility and stale-plan protection in index and migration code.
- Add regression tests for bug fixes and deterministic tests for identity-affecting behavior.
- Publish churn and retrieval-quality evidence together for chunking changes; do not infer retrieval quality from churn alone.
- Keep optional providers and backends behind their interfaces and out of the core installation path.

## Checks

Run these from the repository root before opening a pull request:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy src/cairn_rag
python -m pytest --cov=cairn_rag --cov-branch --cov-report=term-missing
python -m build
```

For website changes, also run:

```bash
cd website
npm ci
npm audit --audit-level=high
npm run lint
npm run typecheck
npm run build
```

Document commands you ran in the pull request. If a check is intentionally omitted, say why.

## Commits and pull requests

- Keep commits narrowly scoped and write imperative commit subjects.
- Explain observable behavior, motivation, validation, and compatibility impact.
- Update user-facing documentation and `CHANGELOG.md` when behavior changes.
- Do not mix mechanical formatting with unrelated functional changes.

By contributing, you agree that your contribution is licensed under the Apache License 2.0.
