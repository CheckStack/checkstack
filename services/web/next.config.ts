import type { NextConfig } from "next";

/** API calls use `/api/*` → `app/api/[...path]/route.ts`, which proxies using runtime `INTERNAL_API_URL`. */
const nextConfig: NextConfig = {
  output: "standalone",
};

export default nextConfig;
