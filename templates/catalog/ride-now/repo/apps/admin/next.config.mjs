// RideNow Ops (operations console). The OmniStack preview serves each app under its own path (BASE_PATH).
const extraDevOrigins = (process.env.ALLOWED_DEV_ORIGINS ?? "").split(",").map((s) => s.trim()).filter(Boolean);

/** @type {import('next').NextConfig} */
export default {
  basePath: process.env.BASE_PATH || "",
  transpilePackages: ["@ridenow/shared"],
  reactStrictMode: true,
  allowedDevOrigins: ["127.0.0.1", ...extraDevOrigins],
  env: { NEXT_PUBLIC_BASE_PATH: process.env.BASE_PATH || "" },
};
