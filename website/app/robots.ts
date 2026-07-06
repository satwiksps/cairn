import type { MetadataRoute } from "next";

import { hasCanonicalSiteUrl, siteUrl } from "@/lib/site";

export default function robots(): MetadataRoute.Robots {
  if (!hasCanonicalSiteUrl) {
    return { rules: { userAgent: "*", disallow: "/" } };
  }

  return {
    rules: { userAgent: "*", allow: "/" },
    sitemap: new URL("/sitemap.xml", siteUrl).toString(),
  };
}
