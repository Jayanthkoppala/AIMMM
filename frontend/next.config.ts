import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  serverExternalPackages: ['got'],
  turbopack: {
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
  async rewrites() {
    // Only use rewrites in development when NEXT_PUBLIC_API_URL is not set
    // In production, use NEXT_PUBLIC_API_URL environment variable directly
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    
    if (!apiUrl || apiUrl.includes('localhost')) {
      // Development: use rewrite to proxy to local backend
      return [
        {
          source: '/api/:path*',
          destination: 'http://localhost:8000/:path*',
        },
      ];
    }
    
    // Production: no rewrites needed, frontend will call API directly
    return [];
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'Cache-Control', value: 'no-store' },
        ],
      },
    ];
  },
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
