/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Standalone output produces a self-contained server bundle for the
  // production container image (web/Dockerfile) — no dev toolchain shipped.
  output: "standalone",
  async rewrites() {
    // Proxy API calls to the Athena backend (SPEC-08). Configurable via env.
    const backend = process.env.ATHENA_API_URL || "http://localhost:8000";
    return [
      // Ops endpoints (/health, /health/full, /metrics, /pilot/status) live at
      // the backend root, outside the /api/v1 envelope. The browser reaches them
      // same-origin via /api/health/* etc., so strip the /api prefix here.
      { source: "/api/health/:path*", destination: `${backend}/health/:path*` },
      { source: "/api/pilot/:path*", destination: `${backend}/pilot/:path*` },
      // Everything else is the versioned REST API (/api/v1/...).
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
    ];
  },
};
export default nextConfig;
