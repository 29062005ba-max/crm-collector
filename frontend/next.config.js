/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  optimizeFonts: false,
  async rewrites() {
    return [
      { source: "/api/:path*", destination: "http://crm_backend:8000/api/:path*" },
    ];
  },
};

module.exports = nextConfig;
