/** @type {import('next').NextConfig} */
// All browser calls go to /api/v1/* on the Next.js origin and are proxied to FastAPI — no CORS needed.
// Local dev: backend on http://localhost:8000. Docker: BACKEND_URL=http://backend:8000 (set in Dockerfile / compose).
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: false },
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${BACKEND_URL}/api/v1/:path*` }];
  },
};

module.exports = nextConfig;
