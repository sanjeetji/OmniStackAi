import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Next.js dev mode blocks cross-origin access to its own HMR/dev assets by default, and treats
  // 127.0.0.1 and localhost as distinct origins for that check. Without this, opening the app via
  // 127.0.0.1 silently prevents client-side JS from hydrating at all - forms then fall back to the
  // browser's native submission (a full-page GET with the fields in the URL), which looks like
  // "nothing happens" with no visible error. Found live (R-471) via the dev server's own warning.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  // PC-101: browsers ask the site root for /favicon.ico before (or instead of) reading the page's
  // icon link - the console's own pages and, now and then, a preview's first page. It was a 404.
  async rewrites() {
    return [{ source: "/favicon.ico", destination: "/icon.svg" }];
  },
};

export default nextConfig;
