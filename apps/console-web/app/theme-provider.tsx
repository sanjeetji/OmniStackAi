"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import type { ComponentProps } from "react";

// Dark-first: every reference platform (Lovable/Bolt/Dyad/Emergent) is a dark-first dev tool.
// `enableSystem` keeps a light preference honored; the explicit toggle lands in Settings (R-495).
export function ThemeProvider({ children, ...props }: ComponentProps<typeof NextThemesProvider>) {
  return (
    <NextThemesProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange {...props}>
      {children}
    </NextThemesProvider>
  );
}
