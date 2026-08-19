import Link from "next/link";

import { GitHubIcon, SteadlithMark } from "@/components/icons";
import { documentationUrl, repositoryUrl } from "@/lib/site";

const navigation = [
  { label: "Why Steadlith", href: "#why" },
  { label: "Architecture", href: "#architecture" },
  { label: "Quick start", href: "#quickstart" },
  { label: "Limitations", href: "#limitations" },
  { label: "Docs", href: documentationUrl },
] as const;

export function SiteHeader() {
  return (
    <header className="site-header">
      <div className="shell flex h-16 items-center justify-between gap-6">
        <Link href="#top" className="brand-link" aria-label="Steadlith home">
          <SteadlithMark className="h-7 w-7 text-[var(--accent)]" />
          <span>Steadlith</span>
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
          {repositoryUrl ? (
            <a
              href={repositoryUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="icon-button"
              aria-label="Open the Steadlith GitHub repository"
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
