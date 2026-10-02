import type { Metadata } from "next";
import { Bricolage_Grotesque, Geist, JetBrains_Mono } from "next/font/google";
import { headers } from "next/headers";
import { ThemeProvider, themeInitScript } from "@/lib/theme";
import { Providers } from "./providers";
import "./globals.css";

const display = Bricolage_Grotesque({ subsets: ["latin"], variable: "--font-bricolage", display: "swap" });
// UI text: Geist over Inter (ADR-0024): tighter and more distinctive at 13–15 px in dense lists.
const ui = Geist({ subsets: ["latin"], variable: "--font-ui", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains", display: "swap" });

export const metadata: Metadata = {
  title: { default: "Jingle", template: "%s · Jingle" },
  description: "See what your friends are playing — on any music app.",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const nonce = (await headers()).get("x-nonce") ?? undefined;
  return (
    <html
      lang="en"
      data-theme="dark"
      suppressHydrationWarning
      className={`${display.variable} ${ui.variable} ${mono.variable}`}
    >
      <head>
        {/* Cover art host: connect early so above-the-fold covers aren't waiting on DNS/TLS. */}
        <link rel="preconnect" href="https://is1-ssl.mzstatic.com" crossOrigin="" />
        <link rel="dns-prefetch" href="https://is1-ssl.mzstatic.com" />
        <script nonce={nonce} dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body>
        <ThemeProvider>
          <Providers>{children}</Providers>
        </ThemeProvider>
      </body>
    </html>
  );
}
