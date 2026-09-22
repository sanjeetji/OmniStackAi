import { createApi } from "@ridenow/shared";

export const api = createApi({
  baseUrl: process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:4000",
  storageKey: "ridenow.admin.session",
});
