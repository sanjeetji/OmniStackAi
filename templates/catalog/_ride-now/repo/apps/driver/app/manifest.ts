import type { MetadataRoute } from "next";

const base = process.env.BASE_PATH || "";

/** Installable PWA: served at <base>/manifest.webmanifest. */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "RideNow Driver",
    short_name: "RN Driver",
    description: "Go online, accept rides and track your earnings.",
    start_url: `${base}/`,
    scope: `${base}/`,
    display: "standalone",
    orientation: "portrait",
    background_color: "#0b0e13",
    theme_color: "#0b0e13",
    icons: [
      { src: `${base}/icon.svg`, sizes: "any", type: "image/svg+xml", purpose: "any" },
      { src: `${base}/icon-maskable.svg`, sizes: "any", type: "image/svg+xml", purpose: "maskable" },
    ],
  };
}
