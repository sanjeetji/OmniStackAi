import { ImageResponse } from "next/og";

/* Generated OpenGraph image (Next's `opengraph-image` file convention, rendered with
 * `ImageResponse` from `next/og` - built into Next, no dependency). Next adds the og:image tags
 * automatically; `metadataBase` in app/layout.tsx makes the URL absolute. Colors approximate
 * the dark theme's OKLCH tokens in sRGB, since the image is a static PNG. */

export const alt = "OmniStackAI: describe the app, get the codebase.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: 72,
          background: "#14161d",
          color: "#eceef3",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <svg width="72" height="72" viewBox="0 0 32 32">
            <rect width="32" height="32" rx="8" fill="#eceef3" />
            <path d="M16 7.5 24.5 12 16 16.5 7.5 12Z" fill="#e3b257" />
            <path
              d="M7.5 16.5 16 21l8.5-4.5M7.5 20.5 16 25l8.5-4.5"
              stroke="#e3b257"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
              opacity="0.75"
            />
          </svg>
          <span style={{ fontSize: 40, fontWeight: 600, letterSpacing: -1 }}>OmniStackAI</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <span style={{ fontSize: 76, fontWeight: 700, lineHeight: 1.05, letterSpacing: -2.5 }}>
            Describe the app. Get the codebase.
          </span>
          <span style={{ fontSize: 30, color: "#a7adbb", lineHeight: 1.3 }}>
            Real Next.js, Python and Go code, a live preview, and a chat to keep changing it.
          </span>
        </div>
      </div>
    ),
    { ...size },
  );
}
