# Security

## Report privately

Do not open a public issue for a suspected vulnerability. Use [GitHub private vulnerability reporting](https://github.com/satwiksps/steadlith/security/advisories/new). If that form is unavailable, use the private contact listed in the repository [security policy](https://github.com/satwiksps/steadlith/blob/main/SECURITY.md).

Include the affected version, configuration or provider, minimal reproduction, expected impact, and disclosure status. Remove credentials and private documents.

## Trust boundaries

Project configuration
: Controls source scope, local state paths, chunking, and provider selection. Review it before granting network access. Paths are contained below the configuration directory.

Source documents
: Must be valid UTF-8 text and can contain hostile terminal markup or unusual Unicode. Human output renders it as literal text; JSON output is encoded safely.

Embedding provider
: Receives missing chunk text when remote. The OpenAI adapter restricts the endpoint and credential variable. Sentence Transformers can download and execute model framework code subject to its own trust settings.

Cache imports
: Are unsigned and can poison retrieval. `--trust-source` records explicit operator approval but performs no authenticity check.

SQLite state
: Contains source text, metadata, vectors, and history. Steadlith validates schema and record integrity but does not encrypt files or authenticate local writers outside operating-system permissions.

Migration receipts
: Have checksums for corruption detection. They are not signed audit records.

## Operator checklist

- Run under a dedicated account with least filesystem privilege.
- Store API keys in the runtime secret manager.
- Grant `--allow-network` only after reviewing config and source scope.
- Protect cache, index, exports, backups, and logs as derived source data.
- Authenticate cache imports out of band.
- Verify after restore, migration, or unexpected termination.
- Keep Python, optional SDKs, model frameworks, and operating system patched.
- Review model and data licenses before local model use or vector redistribution.

For the maintained version and response process, the root `SECURITY.md` is authoritative.
