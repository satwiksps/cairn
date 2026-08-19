# Release process

Steadlith releases are built from an exact `v<version>` tag by the GitHub Actions release workflow. PyPI publication uses trusted publishing rather than a stored API token.

## Prepare

1. Confirm ownership, repository links, PyPI project, Read the Docs project, website, Codecov, and security contact.
2. Set one version in `pyproject.toml`, the source fallback, changelog, and `CITATION.cff`.
3. Date the changelog entry and remove release-specific text from `Unreleased`.
4. Run lint, format, types, tests, coverage, documentation, package build, and website checks.
5. Build wheel and sdist from a clean checkout.
6. Run `twine check` and inspect wheel members and console entry points.
7. Install the wheel into a clean environment and run the documented smoke workflow.
8. Confirm the Read the Docs build for the commit is clean before tagging.

## Publish

1. Enable the repository release variable only for the intended publication window.
2. Create and push the exact tag, for example `v0.3.1` for package version `0.3.1`.
3. Wait for artifact validation and provenance attestation.
4. Confirm GitHub release assets and PyPI files match the workflow artifacts.
5. Install from PyPI in a clean environment.
6. Verify the stable documentation version and website links.
7. Disable the release variable after the window.

The workflow refuses a tag that does not exactly match the package version. Pre-releases are marked on GitHub and are not published to PyPI by the stable publication job.

## After release

- Verify package badges and metadata links.
- Confirm Read the Docs serves the tag and `stable` points to the intended release.
- Run the offline quick start from the published package.
- Check issue templates, private vulnerability reporting, and changelog links.
- Retain artifact checksums and provenance records.

Use the complete [release checklist](../release-checklist.md) for the repository-specific gates.
