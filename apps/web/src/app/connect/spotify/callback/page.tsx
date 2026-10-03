"use client";

import { useEffect, useState } from "react";

/**
 * Spotify login popup lands here (PKCE). It hands the one-time code to the Jingle tab that opened
 * it (same origin only) and closes. Nothing is stored; the code is useless without that tab's verifier.
 */
export default function SpotifyCallback() {
  const [msg, setMsg] = useState("Finishing Spotify login…");
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    const payload = { type: "jingle:spotify", code: p.get("code"), state: p.get("state"), error: p.get("error") };
    if (window.opener && !window.opener.closed) {
      window.opener.postMessage(payload, window.location.origin);
      window.close();
    } else setMsg("You can close this window and go back to Jingle.");
  }, []);
  return (
    <main id="main" className="grid min-h-dvh place-items-center bg-bg p-6 text-sm text-text-muted">
      <h1 className="sr-only">Spotify login</h1>
      <p>{msg}</p>
    </main>
  );
}
