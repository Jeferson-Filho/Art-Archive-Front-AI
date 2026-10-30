/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    // nrs.harvard.edu answers with a 303 to ids.lib.harvard.edu; Vercel's image
    // optimizer checks the redirect target too, so both hosts must be listed
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
