const path = require('path');

/** @type {import('next').NextConfig} */
module.exports = {
  output: "standalone",
  skipMiddlewareUrlNormalize: true,
  skipTrailingSlashRedirect: true,
  experimental: {
    // This is needed for standalone output to work correctly with monorepo
    outputFileTracingRoot: path.join(__dirname, '../'),
  },
};
