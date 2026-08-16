# Release checklist

Use this checklist for every public release. Do not set `CAIRN_RELEASE_ENABLED=true` until the PyPI publisher and release metadata are ready.

## Ownership and namespace

- Confirm the `cairn-rag` PyPI project and trusted publisher configuration.
- Confirm the version and maintainer metadata in `pyproject.toml`, `CHANGELOG.md`, and `CITATION.cff`.
- Confirm the production website URL and repository links.

## Security and governance

- Confirm GitHub private vulnerability reporting is enabled.
- Confirm `SECURITY.md` and `CODE_OF_CONDUCT.md` name monitored private contacts.
- Confirm that the Apache-2.0 copyright notice names the intended owner.

## Evidence

- Keep the recorded TTTD counterexample passing and visible. Do not claim a universal fixed-margin locality guarantee for `tttd-v1`.
- Run churn and retrieval benchmarks together on versioned corpora and update `docs/benchmarks.md` when results change.
- Obtain project-specific legal review before enabling or promoting post-anchor sentence/paragraph snapping.
- Verify current provider prices and terms; do not publish caller-supplied or stale values as current prices.

## Artifact procedure

1. Delete local build artifacts through a scoped, verified path and rebuild from the intended commit.
2. Run `python -m ruff check .`, `python -m ruff format --check .`, `python -m mypy src/cairn_rag`, and `python -m pytest`.
3. Run `python -m build` and `python -m twine check dist/*`.
4. Inspect the wheel: it must contain only the `cairn_rag` package and only the `cairn-rag` console entry point.
5. Install that wheel into a clean environment and smoke-test `python -m cairn_rag`, `cairn-rag --version`, `plan`, `index`, `query --json`, and `verify`.
6. Run `npm ci`, `npm run lint`, `npm run typecheck`, and `npm run build` from `website/`.
7. Tag exactly the version declared in `pyproject.toml`, publish a GitHub release, and enable trusted PyPI publishing only after the preceding checks pass.
