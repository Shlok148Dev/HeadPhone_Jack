import type { NextConfig } from "next";

const config: NextConfig = {
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
  outputFileTracingRoot: new URL("../..", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1"),
  transpilePackages: ["@jingle/design-tokens", "@jingle/ts-client"],
  poweredByHeader: false,
  // Tree-shake named imports from motion (D-PERF-01); components use motion/react-m.
  experimental: { optimizePackageImports: ["motion"] },
  images: {
    // A cover at a fixed release URL never changes; archive.org sends short cache headers (D-ART-07).
    minimumCacheTTL: 60 * 60 * 24 * 30,
    remotePatterns: [
      { protocol: "https", hostname: "coverartarchive.org" },
      { protocol: "https", hostname: "*.archive.org" },
      { protocol: "https", hostname: "i.scdn.co" },
      { protocol: "https", hostname: "*.mzstatic.com" },
    ],
  },
};

export default config;
