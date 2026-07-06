import type { MetadataRoute } from "next";

import { hasCanonicalSiteUrl, siteUrl } from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  if (!hasCanonicalSiteUrl) {
    return [];
  }

  return [
    {
      url: siteUrl.toString(),
      changeFrequency: "monthly",
      priority: 1,
    },
  ];
}
