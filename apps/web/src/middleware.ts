import { NextResponse, type NextRequest } from "next/server";

/**
 * Strict Content-Security-Policy with a per-request nonce, applied site-wide; pages can never be
 * framed. The Companion pairing page (/connect/companion) allows no third-party origin at all
 * (S2-EXT-security M3); elsewhere Google Identity Services is the only third-party script.
 */
export function middleware(request: NextRequest) {
  const nonce = btoa(crypto.randomUUID());
  const dev = process.env.NODE_ENV !== "production";
  const google = !request.nextUrl.pathname.startsWith("/connect/companion");
  const csp = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}'${google ? " https://accounts.google.com/gsi/client" : ""}${dev ? " 'unsafe-eval'" : ""}`,
    `style-src 'self' 'unsafe-inline'${google ? " https://accounts.google.com/gsi/style" : ""}`,
    google ? "frame-src https://accounts.google.com" : "frame-src 'none'",
    "worker-src 'self'",
    "img-src 'self' data: blob: https://coverartarchive.org https://*.archive.org https://i.scdn.co https://*.mzstatic.com",
    "font-src 'self' data:",
    `connect-src 'self'${google ? " https://accounts.google.com/gsi/" : ""}`,
    "frame-ancestors 'none'",
    "base-uri 'none'",
    "form-action 'self'",
    "object-src 'none'",
  ].join("; ");

  const headers = new Headers(request.headers);
  headers.set("x-nonce", nonce);
  headers.set("Content-Security-Policy", csp);
  const response = NextResponse.next({ request: { headers } });
  response.headers.set("Content-Security-Policy", csp);
  return response;
}

export const config = {
  matcher: [{ source: "/((?!_next/static|_next/image|favicon.ico|healthz).*)" }],
};
