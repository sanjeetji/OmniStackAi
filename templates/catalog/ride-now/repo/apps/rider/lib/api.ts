import { createApi } from "@ridenow/shared";

/** Browser calls go to NEXT_PUBLIC_API_URL (the preview's proxied path, or the API's own URL). */
export const api = createApi({
  baseUrl: process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:4000",
  storageKey: "ridenow.rider.session",
});

/** App paths for plain `window.location` navigation, which does not add the base path itself. */
export const withBase = (path: string) => `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}${path}`;
