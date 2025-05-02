/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    domains: [
      'avatars.githubusercontent.com',
      'github.com',
      'img.clerk.com',
      'images.clerk.dev',
      'localhost',
    ],
  },
}

module.exports = nextConfig
