/** @type {import('next').NextConfig} */
const nextConfig = {
  // TypeScript and ESLint errors must fail the build.
  // Do not re-add ignoreBuildErrors or ignoreDuringBuilds.

  async rewrites() {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL;
    const realtimeBase = process.env.NEXT_PUBLIC_REALTIME_URL;
    if (!apiBase || !realtimeBase) return [];
    return [
      { source: '/api/:path*', destination: `${apiBase}/api/:path*` },
      { source: '/realtime/:path*', destination: `${realtimeBase}/:path*` },
    ];
  },

  async headers() {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? '';
    const realtimeBase = process.env.NEXT_PUBLIC_REALTIME_URL ?? '';
    const apiOrigin = apiBase.replace(/\/+$/, '');
    const realtimeOrigin = realtimeBase.replace(/\/+$/, '');
    const connectSrc = [
      "'self'",
      'https://*.supabase.co',
      apiOrigin,
      realtimeOrigin,
    ].filter(Boolean).join(' ');

    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(self), geolocation=()' },
          {
            key: 'Content-Security-Policy',
            value: `default-src 'self'; connect-src ${connectSrc}; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:;`,
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
