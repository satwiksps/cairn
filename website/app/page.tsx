import Link from "next/link";

import {
  CheckIcon,
  GitHubIcon,
  ShieldIcon,
  SteadlithMark,
} from "@/components/icons";
import { SiteHeader } from "@/components/site-header";
import { TerminalWindow } from "@/components/terminal-window";
import { documentationUrl, packageUrl, repositoryUrl } from "@/lib/site";

const capabilities = [
  {
    number: "01",
    title: "Content-defined identities",
    body: "Versioned hashes separate canonical chunk content from source offsets and embedding-model identity.",
  },
  {
    number: "02",
    title: "Cache-aware planning",
    body: "Preview add, keep, move, and delete operations without writing state or calling a provider.",
  },
  {
    number: "03",
    title: "Transactional indexing",
    body: "Apply one validated SQLite snapshot. Removed occurrences become inactive tombstones immediately.",
  },
  {
    number: "04",
    title: "Verifiable state",
    body: "Manifests, Merkle roots, generation checks, and record digests make committed state explicit.",
  },
] as const;

const architectureSteps = [
  ["01", "Chunk", "Normalize words and select rolling Rabin fingerprint boundaries."],
  ["02", "Identify", "Hash canonical content with versioned normalization and chunking parameters."],
  ["03", "Plan", "Compare manifests and price only known embedding cache misses."],
  ["04", "Apply", "Reuse vectors, embed misses, tombstone removals, and commit atomically."],
] as const;

const safeguards = [
  ["Network access", "Optional providers require --allow-network."],
  ["Deletion", "Deleting plans require --allow-delete; emptying an index also requires --allow-empty."],
  ["Source scope", "Paths and resolved symlinks must stay inside the configuration directory."],
  ["Imported state", "Unsigned cache imports require --trust-source; compaction supports dry run."],
] as const;

const support = [
  ["Index", "Transactional SQLite, one logical index per database"],
  ["Embeddings", "Offline lexical, optional OpenAI and sentence-transformers"],
  ["Chunking", "Rabin CDC, opt-in snapping, comparison strategies"],
  ["State", "Cache, manifests, Merkle roots, tombstones, verification"],
  ["Measurement", "Published five-corpus churn and retrieval regressions"],
  ["Output", "Human-readable terminal tables and machine-readable JSON"],
] as const;

export default function Home() {
  return (
    <div id="top" className="min-h-screen overflow-hidden">
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <SiteHeader />

      <main id="main-content">
        <section className="hero-section shell">
          <div className="hero-grid">
            <div className="hero-copy">
              <div className="eyebrow">
                <span className="eyebrow-mark" /> Open source. Apache-2.0. Python 3.10+.
              </div>
              <h1>Incremental indexing for RAG corpora that change.</h1>
              <p className="hero-lede">
                Steadlith combines content-defined chunk identities, cache-aware planning, and
                transactional updates so every revision becomes an explicit, inspectable index
                operation.
              </p>
              <div className="hero-actions">
                <Link href="#quickstart" className="primary-button">
                  Read the quick start
                </Link>
                <Link href="#architecture" className="secondary-button">
                  See the architecture
                </Link>
              </div>
              <div className="install-line" aria-label="Installation command">
                <span className="prompt">$</span>
                <code>python -m pip install steadlith</code>
              </div>
              <p className="release-note">
                Install the current release from{" "}
                <a href={packageUrl} target="_blank" rel="noopener noreferrer">
                  PyPI
                </a>
                .
              </p>
            </div>

            <TerminalWindow />
          </div>

          <div className="principle-strip" aria-label="Project principles">
            <span>Rabin CDC</span>
            <span>Dry-run planning</span>
            <span>Transactional SQLite</span>
            <span>Offline by default</span>
          </div>
        </section>

        <section id="why" className="section shell scroll-mt-24">
          <div className="section-intro section-intro-wide">
            <p className="section-label">WHY STEADLITH</p>
            <h2>A small edit should be visible as a small change plan.</h2>
            <p>
              Offset-based chunking can shift downstream boundaries after an early insertion,
              changing hashes for content that is otherwise unchanged. Steadlith places candidate
              boundaries from a rolling fingerprint over normalized words, then compares
              versioned manifests to classify what changed.
            </p>
          </div>

          <div className="positioning-line">
            <span className="positioning-rule" aria-hidden="true" />
            <p>
              A focused indexing layer, not another RAG framework. Steadlith sits below
              orchestration libraries and above embedding and vector providers.
            </p>
          </div>

          <div className="capability-grid">
            {capabilities.map((capability) => (
              <article key={capability.number} className="capability-card">
                <span className="card-number">{capability.number}</span>
                <h3>{capability.title}</h3>
                <p>{capability.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="architecture" className="section section-bordered scroll-mt-16">
          <div className="shell">
            <div className="section-intro">
              <p className="section-label">ARCHITECTURE</p>
              <h2>A pure core. Effects at the edge.</h2>
              <p>
                Chunking and content identity stay deterministic. Files, credentials, providers,
                and databases enter only through explicit application boundaries.
              </p>
            </div>

            <div className="architecture-flow" aria-label="Steadlith indexing architecture">
              <div className="flow-node">
                <span>Input</span>
                <strong>Source text</strong>
              </div>
              <div className="flow-connector" aria-hidden="true" />
              <div className="flow-node">
                <span>Pure core</span>
                <strong>Chunk + identify</strong>
              </div>
              <div className="flow-connector" aria-hidden="true" />
              <div className="flow-node">
                <span>State diff</span>
                <strong>Manifest plan</strong>
              </div>
              <div className="flow-connector" aria-hidden="true" />
              <div className="flow-node flow-node-accent">
                <span>Effects</span>
                <strong>Cache + index</strong>
              </div>
            </div>

            <div className="architecture-steps">
              {architectureSteps.map(([number, title, body]) => (
                <article key={number}>
                  <span>{number}</span>
                  <h3>{title}</h3>
                  <p>{body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="quickstart" className="section shell scroll-mt-20">
          <div className="quickstart-grid">
            <div className="section-intro">
              <p className="section-label">CLI WORKFLOW</p>
              <h2>Start offline. Inspect every transition.</h2>
              <p>
                The starter config uses deterministic local lexical embeddings, so indexing and
                keyword retrieval work without credentials or network access.
              </p>
              <div className="inline-note">
                Select a learned provider when queries require semantic similarity or synonyms.
              </div>
            </div>

            <div className="code-panel" aria-label="Steadlith quick start commands">
              <div className="code-panel-header">
                <span>quick-start.sh</span>
                <span>offline</span>
              </div>
              <pre>
                <code>
                  <span className="code-muted"># create a local configuration</span>{"\n"}
                  <span className="code-command">steadlith init</span>{"\n\n"}
                  <span className="code-muted"># inspect before any write</span>{"\n"}
                  <span className="code-command">steadlith plan</span>{"\n\n"}
                  <span className="code-command">steadlith index</span>{"\n"}
                  <span className="code-command">steadlith status</span>{"\n"}
                  <span className="code-command">steadlith query &quot;release policy&quot;</span>{"\n"}
                  <span className="code-command">steadlith verify</span>
                </code>
              </pre>
            </div>
          </div>

          <div className="scope-note">
            <ShieldIcon className="h-5 w-5 shrink-0 text-[var(--accent)]" />
            <p>
              Positional paths describe the complete desired corpus, not additions. Prefer
              committed source globs and inspect the plan before applying changes.
            </p>
          </div>
        </section>

        <section className="section section-bordered">
          <div className="shell safeguards-grid">
            <div className="section-intro">
              <p className="section-label">OPERATIONAL SAFETY</p>
              <h2>Destructive and networked work stays explicit.</h2>
              <p>
                <code>plan</code> is the safe entry point: it makes no writes and sends no content
                to an embedding provider.
              </p>
            </div>

            <div className="safeguard-list">
              {safeguards.map(([title, body]) => (
                <div className="safeguard-row" key={title}>
                  <CheckIcon className="mt-0.5 h-4 w-4 shrink-0 text-[var(--accent)]" />
                  <div>
                    <h3>{title}</h3>
                    <p>{body}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="section shell">
          <div className="section-intro section-intro-wide">
            <p className="section-label">CURRENT SUPPORT</p>
            <h2>A deliberately narrow supported core.</h2>
            <p>
              The reference path is implemented end to end. Additional backends are not presented
              as supported until they pass the shared adapter conformance suite.
            </p>
          </div>

          <dl className="support-table" aria-label="Current Steadlith support">
            {support.map(([component, detail]) => (
              <div className="support-row" key={component}>
                <dt className="support-component">{component}</dt>
                <dd className="support-detail">{detail}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section id="limitations" className="section limitation-section scroll-mt-16">
          <div className="shell limitation-grid">
            <div>
              <p className="section-label section-label-warm">HONEST LIMITATIONS</p>
              <h2>Limits stay explicit.</h2>
            </div>
            <div className="limitation-copy">
              <p className="limitation-lede">
                TTTD v1 is regression-tested for churn, but it does not claim a universal
                fixed-distance locality proof.
              </p>
              <p>
                The stateful fallback can remain out of phase until a common primary boundary.
                Steadlith keeps the counterexample as a regression and reports measured churn
                instead of turning an empirical result into a theorem.
              </p>
              <p>
                Across the bundled five-corpus benchmark, default CDC re-embeds 32.7% of revised
                chunks versus 53.3% for fixed chunking, with recall@5 of 1.0 under both offline
                scorers. Structural snapping remains opt-in and requires project-specific review.
              </p>
            </div>
          </div>
        </section>

        <section id="open-source" className="final-section shell">
          <SteadlithMark className="mx-auto h-10 w-10 text-[var(--accent)]" />
          <p className="section-label mt-7">APACHE-2.0 OPEN SOURCE</p>
          <h2>Evaluate Steadlith on your corpus.</h2>
          <p>
            Start offline, inspect the delta, then measure churn and retrieval quality before
            connecting a paid provider.
          </p>
          <div className="final-actions">
            <a
              href={documentationUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="primary-button"
            >
              Read the documentation
            </a>
            {repositoryUrl ? (
              <a
                href={repositoryUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="secondary-button"
              >
                <GitHubIcon className="h-4 w-4" /> View on GitHub
              </a>
            ) : null}
            <a
              href={packageUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="secondary-button"
            >
              View on PyPI
            </a>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="shell footer-grid">
          <div className="footer-brand">
            <SteadlithMark className="h-6 w-6 text-[var(--accent)]" />
            <span>Steadlith</span>
          </div>
          <p>Stable identities. Inspectable plans. Explicit state.</p>
          <div className="footer-links">
            <Link href="#top">Back to top</Link>
            {repositoryUrl ? (
              <a href={repositoryUrl} target="_blank" rel="noopener noreferrer">
                Source
              </a>
            ) : null}
            <a href={packageUrl} target="_blank" rel="noopener noreferrer">
              PyPI
            </a>
            <a href={documentationUrl} target="_blank" rel="noopener noreferrer">
              Docs
            </a>
            <span>Apache License 2.0</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
