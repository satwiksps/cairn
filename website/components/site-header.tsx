import Link from "next/link";

import { CairnMark, GitHubIcon } from "@/components/icons";
import { repositoryUrl, site } from "@/lib/site";

const navigation = [
  { label: "Why Cairn", href: "#why" },
  { label: "Architecture", href: "#architecture" },
  { label: "Quick start", href: "#quickstart" },
  { label: "Limitations", href: "#limitations" },
] as const;

export function SiteHeader() {
  return (
    <header className="site-header">
      <div className="shell flex h-16 items-center justify-between gap-6">
        <Link href="#top" className="brand-link" aria-label="Cairn home">
          <CairnMark className="h-7 w-7 text-[var(--accent)]" />
          <span>Cairn</span>
        </Link>

        <nav
          aria-label="Primary navigation"
          className="hidden items-center gap-5 md:flex xl:gap-7"
        >
          {navigation.map((item) => (
            <Link key={item.href} href={item.href} className="nav-link">
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2.5">
          <span className="version-badge hidden xl:inline-flex">{site.version}</span>
          {repositoryUrl ? (
            <a
              href={repositoryUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="icon-button"
              aria-label="Open the Cairn GitHub repository"
            >
              <GitHubIcon className="h-[18px] w-[18px]" />
            </a>
          ) : null}
          <Link href="#quickstart" className="small-button">
            Get started
          </Link>
        </div>
      </div>
    </header>
  );
}
