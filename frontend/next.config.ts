import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Externalize server-only packages
  serverExternalPackages: ['got'],
  // Turbopack configuration to handle module resolution issues
  experimental: {
    turbo: {
      // Resolve extensions in order
      resolveExtensions: [
        '.mdx',
        '.tsx',
        '.ts',
        '.jsx',
        '.js',
        '.mjs',
        '.json',
      ],
    },
  },
  // Webpack fallback for non-Turbopack builds
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        got: false,
      };
    }
    return config;
  },
};

export default nextConfig;

