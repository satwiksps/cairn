# Steadlith website

The public landing page is a standalone Next.js application inside the Python repository.

## Local development

Requires Node.js 24.x and npm 11.x.

```bash
cd website
npm ci
npm run dev
```

Before committing a change:

```bash
npm run lint
npm run typecheck
npm run build
```

## Deploying to Vercel

Import the repository and set **Root Directory** to `website`. Vercel detects Next.js and uses the committed `package-lock.json`; no custom build or output directory is needed.

Set `NEXT_PUBLIC_SITE_URL` to the canonical `https://` production URL. GitHub links default to the upstream `https://github.com/satwiksps/steadlith`; forks can override them with `NEXT_PUBLIC_REPOSITORY_URL`.

The production URL is also inferred from Vercel's `VERCEL_PROJECT_PRODUCTION_URL` when `NEXT_PUBLIC_SITE_URL` is absent. If neither value is available, canonical metadata is omitted, robots disallow indexing, and the sitemap stays empty instead of publishing a localhost URL.
