# Security policy

## Supported versions

Security fixes are applied to the latest released `0.1.x` version and the `main` branch. Older alpha versions are not maintained.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability.

Use [GitHub private vulnerability reporting](https://github.com/satwiksps/cairn/security/advisories/new). If that form is unavailable, email **sahoospsatwik@gmail.com** with the subject `Cairn security report`.

Include, when possible:

- the affected version or commit;
- the configuration, provider, or backend involved;
- reproduction steps or a minimal proof of concept;
- the expected impact and any known workaround;
- whether the report has been disclosed elsewhere.

Remove credentials and private source documents. Use synthetic data unless the sensitive material is essential to understanding the issue.

The maintainer will acknowledge a report within 72 hours, keep the reporter informed while it is investigated, and coordinate disclosure after a fix is available. This is an acknowledgement target, not a guaranteed resolution time.

## Security boundaries

Cairn processes user-selected documents and can send their contents to a configured embedding provider. Review configuration before use, keep provider credentials in environment variables, and grant `--allow-network` only when the destination is trusted.

Cache imports are unsigned and must come from a trusted source. SQLite database, cache, manifest, migration receipt, and configuration files should be protected with normal operating-system access controls. Cairn does not provide encryption at rest or sandbox third-party embedding models.

The deterministic hash embedder is test infrastructure and provides no confidentiality or production retrieval guarantees.
