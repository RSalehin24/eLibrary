import type { NextConfig } from "next";

const apiOrigin = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";

const configuration: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  agentRules: false,
  trailingSlash: true,
  experimental: { proxyClientMaxBodySize: "32mb" },
  async redirects() { return [{ source: "/epub-reader/index.html", destination: "/local-reader/", permanent: false }, { source: "/epub-reader", destination: "/local-reader/", permanent: false }]; },
  async headers() { return [{ source: "/sw.js", headers: [{ key: "Content-Type", value: "text/javascript; charset=utf-8" }, { key: "Cache-Control", value: "no-store" }, { key: "Service-Worker-Allowed", value: "/" }, { key: "X-Content-Type-Options", value: "nosniff" }] }]; },
  async rewrites() {
    return [
      { source: "/api/v1/reading/sessions/:identifier/resources/:path*", destination: `${apiOrigin}/api/v1/reading/sessions/:identifier/resources/:path*` },
      { source: "/api/:path*/", destination: `${apiOrigin}/api/:path*/` },
    ];
  },
};

export default configuration;
