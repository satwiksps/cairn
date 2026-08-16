## Summary

<!-- What user-visible or internal behavior changes? Keep this focused. -->

## Motivation

<!-- What problem does this solve? Link the issue when one exists. -->

## Validation

<!-- List tests and commands run. Include measured churn/retrieval evidence for algorithm changes. -->

- [ ] `python -m ruff check .`
- [ ] `python -m ruff format --check .`
- [ ] `python -m mypy src/steadlith`
- [ ] `python -m pytest`
- [ ] `python -m build`

## Compatibility and safety

<!-- Explain effects on chunk identity, cache keys, manifests, deletion, migrations, provider spend, and optional dependencies. Write "none" only after checking. -->

## Checklist

- [ ] The change is scoped to one concern.
- [ ] Tests cover the new or changed behavior.
- [ ] User-facing behavior and configuration are documented.
- [ ] Pure core modules remain free of I/O, network, environment, and config lookups.
- [ ] Embedding model identity remains outside the chunk hash.
- [ ] New logs, fixtures, and examples contain no secrets or private corpus data.
- [ ] I called out any intentional compatibility break and supplied a migration path.
