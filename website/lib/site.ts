function readHttpsUrl(name: string, value: string | undefined, hostOnly = false): URL | undefined {
  const input = value?.trim();
  if (!input) {
    return undefined;
  }

  let parsed: URL;
  try {
    parsed = new URL(hostOnly ? `https://${input}` : input);
  } catch {
    throw new Error(`${name} must be an absolute HTTPS URL.`);
  }

  if (parsed.protocol !== "https:" || parsed.username || parsed.password) {
    throw new Error(`${name} must be an absolute HTTPS URL without credentials.`);
  }

  return parsed;
}

const configuredSiteUrl = readHttpsUrl(
  "NEXT_PUBLIC_SITE_URL",
  process.env.NEXT_PUBLIC_SITE_URL,
);
const vercelSiteUrl = readHttpsUrl(
  "VERCEL_PROJECT_PRODUCTION_URL",
  process.env.VERCEL_PROJECT_PRODUCTION_URL,
  true,
);
const canonicalUrl = configuredSiteUrl ?? vercelSiteUrl;

export const hasCanonicalSiteUrl = canonicalUrl !== undefined;

export const siteUrl = new URL(canonicalUrl ?? "http://localhost:3000");

export const repositoryUrl = readHttpsUrl(
  "NEXT_PUBLIC_REPOSITORY_URL",
  process.env.NEXT_PUBLIC_REPOSITORY_URL ?? "https://github.com/satwiksps/cairn",
)?.toString();

export const packageUrl = "https://pypi.org/project/cairn-rag/";

export const site = {
  name: "Cairn",
  title: "Cairn — Incremental indexing for changing RAG corpora",
  description:
    "Content-defined chunk identities, cache-aware planning, and transactional indexing for RAG corpora that change.",
  version: "v0.1.0 alpha",
} as const;
