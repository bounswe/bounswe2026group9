import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    const backend = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8888";
    return [
      {
        source: "/api/proxy/:path*",
        destination: `${backend}/:path*`,
      },
    ];
  },
};

export default nextConfig;
