/** Runtime configuration. Everything comes from the environment; .env.example lists every key. */
function required(name: string, fallback?: string): string {
  const value = process.env[name] ?? fallback;
  if (value === undefined || value === "") throw new Error(`${name} is not set`);
  return value;
}

const preview = process.env.OMNISTACK_PREVIEW === "1";

export const config = {
  port: Number(process.env.PORT ?? 4000),
  databaseUrl: required("DATABASE_URL", "postgresql://localhost:5432/ridenow"),
  jwtSecret: required("JWT_SECRET", preview ? "preview-only-secret-change-me" : undefined),
  accessTtlSeconds: 15 * 60,
  refreshTtlDays: 30,
  /** In the local preview: simulated drivers accept and drive, and OTP 123456 is accepted. */
  preview,
  simulation: (process.env.DEMO_SIMULATION ?? (preview ? "1" : "0")) === "1",
  corsOrigin: process.env.CORS_ORIGIN ?? "*",
  currency: "INR",
  city: { name: "Bengaluru", lat: 12.9716, lng: 77.5946 },
};

if (!preview && config.jwtSecret.length < 32) {
  throw new Error("JWT_SECRET must be at least 32 characters outside the preview");
}
