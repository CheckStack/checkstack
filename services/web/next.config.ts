import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    const internal = process.env.INTERNAL_API_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${internal}/:path*` }];
  },
};

export default nextConfig;
