/** Environment and server configuration for CareClinic API. */

export interface Config {
  port: number;
  databaseUrl: string;
  jwtSecret: string;
  corsOrigin: string;
  isDev: boolean;
  isPreview: boolean;
}

export function loadConfig(): Config {
  const port = parseInt(process.env.PORT || "4000", 10);
  const databaseUrl =
    process.env.DATABASE_URL ||
    "postgres://omnistackai:omnistackai@127.0.0.1:5432/care_clinic";
  const jwtSecret =
    process.env.JWT_SECRET ||
    "careclinic-development-secret-change-me-in-production-min-32-chars";
  const corsOrigin = process.env.CORS_ORIGIN || "*";
  const isDev = process.env.NODE_ENV !== "production";
  const isPreview = process.env.OMNISTACK_PREVIEW === "1";

  return {
    port,
    databaseUrl,
    jwtSecret,
    corsOrigin,
    isDev,
    isPreview,
  };
}

export const config = loadConfig();
