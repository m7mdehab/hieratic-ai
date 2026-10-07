import type { NextConfig } from "next";

// The page is statically rendered: the loader (src/lib/state.ts) reads the
// canonical files in the parent directory at build time (or from
// DASHBOARD_REPO_ROOT). No runtime file tracing is required.
const nextConfig: NextConfig = {
  reactStrictMode: true,
};

export default nextConfig;
