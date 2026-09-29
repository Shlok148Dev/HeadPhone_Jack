import type { NextConfig } from "next";

const config: NextConfig = {
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
  outputFileTracingRoot: new URL("../..", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1"),
  transpilePackages: ["@jingle/design-tokens", "@jingle/ts-client"],
  poweredByHeader: false,
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "coverartarchive.org" },
      { protocol: "https", hostname: "*.archive.org" },
      { protocol: "https", hostname: "i.scdn.co" },
      { protocol: "https", hostname: "*.mzstatic.com" },
    ],
  },
};

export default config;
