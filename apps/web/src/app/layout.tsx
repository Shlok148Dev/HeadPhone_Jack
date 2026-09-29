import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Jingle",
  description: "See what your friends are playing — on any music app.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark">
      <body>{children}</body>
    </html>
  );
}
