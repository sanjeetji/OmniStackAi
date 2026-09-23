// CareClinic patient portal app. The OmniStack preview serves each app under its own basePath.
const extraDevOrigins = (process.env.ALLOWED_DEV_ORIGINS ?? "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);

/** @type {import('next').NextConfig} */
export default {
  basePath: process.env.BASE_PATH || "",
  transpilePackages: ["@careclinic/shared"],
  reactStrictMode: true,
  allowedDevOrigins: ["127.0.0.1", ...extraDevOrigins],
  env: { NEXT_PUBLIC_BASE_PATH: process.env.BASE_PATH || "" },
};
