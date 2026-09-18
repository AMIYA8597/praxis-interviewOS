/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['@praxis/ui', '@praxis/types', '@praxis/config', '@praxis/schemas'],
}

module.exports = nextConfig
