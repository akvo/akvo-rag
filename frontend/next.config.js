const path = require("path");

/** @type {import('next').NextConfig} */
module.exports = {
  output: "standalone",
  skipMiddlewareUrlNormalize: true,
  skipTrailingSlashRedirect: true,
  experimental: {
    // This is needed for standalone output to work correctly with monorepo
    outputFileTracingRoot: path.join(__dirname, "../"),
  },
  async rewrites() {
    const backendUrl =
      process.env.INTERNAL_BACKEND_URL || "http://backend:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: "/openapi/:path*",
        destination: `${backendUrl}/openapi/:path*`,
      },
    ];
  },
};
