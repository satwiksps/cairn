import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { hasCanonicalSiteUrl, site, siteUrl } from "@/lib/site";

import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: siteUrl,
  title: site.title,
  description: site.description,
  applicationName: site.name,
  keywords: [
    "RAG",
    "incremental indexing",
    "content-defined chunking",
    "embeddings",
    "vector index",
    "open source",
  ],
  alternates: hasCanonicalSiteUrl ? { canonical: "/" } : undefined,
  openGraph: hasCanonicalSiteUrl
    ? {
        type: "website",
        url: "/",
        title: site.title,
        description: site.description,
        siteName: site.name,
        images: [
          {
            url: "/cairn-social-card.jpg",
            width: 1732,
            height: 908,
            alt: "Cairn social card",
          },
        ],
      }
    : undefined,
  twitter: hasCanonicalSiteUrl
    ? {
        card: "summary_large_image",
        title: site.title,
        description: site.description,
        images: ["/cairn-social-card.jpg"],
      }
    : undefined,
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#080a0b",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
