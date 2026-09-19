"use client";

/** Root-layout error boundary (Next `global-error.js`). Per the docs it replaces the root layout
 * and receives no global styles, fonts or theme - so it ships its own `<html>`/`<body>` with a
 * few inline styles that match the dark theme's tokens. Rarely reached; kept deliberately small. */
export default function GlobalError({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          background: "#14161d",
          color: "#eceef3",
          fontFamily: "ui-sans-serif, system-ui, sans-serif",
        }}
      >
        <main style={{ textAlign: "center", padding: 24, maxWidth: 480 }}>
          <p style={{ fontFamily: "ui-monospace, monospace", fontSize: 13, color: "#a7adbb", margin: 0 }}>
            500
          </p>
          <h1 style={{ fontSize: 28, letterSpacing: "-0.02em", margin: "8px 0 12px" }}>
            Something went wrong
          </h1>
          <p style={{ color: "#a7adbb", margin: 0, lineHeight: 1.5 }}>
            The console could not render this page.
            {error.digest ? ` Reference ${error.digest}.` : ""}
          </p>
          <button
            type="button"
            onClick={() => retry()}
            style={{
              marginTop: 24,
              padding: "8px 14px",
              borderRadius: 10,
              border: "1px solid rgba(255,255,255,0.14)",
              background: "#eceef3",
              color: "#14161d",
              font: "inherit",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            Try again
          </button>
        </main>
      </body>
    </html>
  );
}
