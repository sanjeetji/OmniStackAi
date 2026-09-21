export const metadata = { title: "Corner Shop" };

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 32 }}>{children}</body>
    </html>
  );
}
