/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    // Harvard's image server (nrs.harvard.edu, which redirects to ids.lib.harvard.edu)
    // refuses the fetch made by Vercel's image optimizer (502
    // OPTIMIZED_EXTERNAL_IMAGE_REQUEST_UNAUTHORIZED), while browsers load it fine, so
    // the images are served straight from Harvard instead of through the optimizer
    unoptimized: true,
    domains: ["nrs.harvard.edu", "ids.lib.harvard.edu"]
  },
  async redirects() {
    return [
      {
        source: "/",
        destination: "/home",
        permanent: true
      }
    ];
  },
  reactStrictMode: false
};

export default nextConfig;
