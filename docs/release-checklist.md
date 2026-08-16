# Release checklist

Cairn's code and distributions can be built locally, but public publishing is intentionally gated. Do not set the repository variable `CAIRN_RELEASE_ENABLED=true` until every owner-specific item below is complete.

## Ownership and namespace

- Reserve the `cairn-rag` distribution name under the intended PyPI organization. The unrelated `cairn` distribution, module, and command are already occupied.
- Add the accountable maintainer or organization to package metadata and `CITATION.cff`.
- Choose the production website domain, configure Vercel with `website/` as its root, and set `NEXT_PUBLIC_SITE_URL` to the real HTTPS URL.

## Security and governance

- Enable GitHub private vulnerability reporting.
- Replace the fallback profile instruction in `SECURITY.md` with a monitored private security address or form.
- Name a private Code of Conduct enforcement contact.
- Confirm that the Apache-2.0 copyright notice names the intended owner.

## Evidence

- Keep the recorded TTTD counterexample passing and visible. Do not claim the proposed fixed-margin locality guarantee unless a replacement strategy satisfies that acceptance criterion.
- Run churn and retrieval benchmarks together on versioned corpora and publish the raw machine-readable output.
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
