import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OmniStackAI Console",
  description:
    "One application IR -> owned code, preview plans, verification gates, and focused edits.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
