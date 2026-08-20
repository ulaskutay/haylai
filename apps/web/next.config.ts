import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  serverExternalPackages: ["ffmpeg-static"],
  allowedDevOrigins: [
    "127.0.0.1",
    "localhost",
    "*.trycloudflare.com",
  ],
  experimental: {
    proxyClientMaxBodySize: "25mb",
  },
};

export default nextConfig;
