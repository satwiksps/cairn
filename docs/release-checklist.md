# Release checklist

Use this checklist for every public release. Set `STEADLITH_RELEASE_ENABLED=true` only for an intended publishing window after verifying the GitHub environment, PyPI trusted publisher, and release metadata.

## Ownership and namespace

- Confirm the `steadlith` PyPI project and trusted publisher configuration.
- Confirm the version and maintainer metadata in `pyproject.toml`, `CHANGELOG.md`, and `CITATION.cff`.
- Confirm the production website URL and repository links.

The following one-time setup was required for the first Steadlith release. Re-verify it after renaming or transferring the repository:

- Rename the GitHub repository to `satwiksps/steadlith` before creating the release tag.
- On PyPI, create a pending trusted publisher for project `steadlith`, owner `satwiksps`, repository `steadlith`, workflow `release.yml`, and environment `pypi`.
- Keep the existing PyPI releases under their old distribution name as historical upgrade sources. Publish new versions only as `steadlith`.
- Create or verify the GitHub `pypi` environment, then set the repository Actions variable `STEADLITH_RELEASE_ENABLED=true` only when publishing is ready.
- After the new release is verified, remove the obsolete `CAIRN_RELEASE_ENABLED` variable and the old distribution's trusted publisher. Do not delete its published releases.
- Activate the repository in Codecov and verify that OIDC uploads are accepted before requiring coverage uploads in CI.
- Create the Steadlith Vercel project, set `NEXT_PUBLIC_SITE_URL` to its canonical URL, and verify `NEXT_PUBLIC_REPOSITORY_URL` if it is overridden.
- Import `satwiksps/steadlith` at Read the Docs with project slug `steadlith`, keep `.readthedocs.yaml` as the configuration path, and verify the `latest` build at `steadlith.readthedocs.io`.

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
2. Run `python -m ruff check .`, `python -m ruff format --check .`, `python -m mypy src/steadlith`, and `python -m pytest`.
3. Run `python -m build` and `python -m twine check dist/*`.
4. Inspect the wheel: it must contain only the `steadlith` package and only the `steadlith` console entry point.
5. Install that wheel into a clean environment and smoke-test `python -m steadlith`, `steadlith --version`, `plan`, `index`, `query --json`, `verify`, and adoption of a disposable 0.2 fixture.
6. Run `npm ci`, `npm run lint`, `npm run typecheck`, and `npm run build` from `website/`.
7. Run the Sphinx documentation build with warnings as errors and confirm the commit builds successfully on Read the Docs.
8. Confirm the Codecov upload succeeded and the README badge resolves to the current default-branch coverage.
9. Tag exactly the version declared in `pyproject.toml`, publish a GitHub release, and enable trusted PyPI publishing only after the preceding checks pass.
10. Verify the tag appears as a documentation version and that `stable` resolves to the intended public release.
