"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { Blip, Button } from "@/components/ds";
import { FocusShell } from "@/components/app/FocusShell";
import { FormAlert } from "@/components/app/forms";
import { ApiError, api, json } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Phase = "detecting" | "ready" | "missing" | "consent" | "pairing" | "paired" | "manual" | "error";

const PAIR_ERRORS: Record<string, string> = {
  invalid_token: "That didn't work. Try connecting again.",
  unreachable: "The Companion couldn't reach Jingle. Check the Jingle address in the Companion, then try again.",
  wrong_origin: "The Companion is set up for a different Jingle address. Open the Companion and check its settings.",
  extension_error: "The Companion hit a problem. Try again.",
};

function safeReturn(v: string | null): string {
  return v && v.startsWith("/") && !v.startsWith("//") ? v : "/settings/connections";
}

/**
 * Companion pairing (CONTRACTS.md §11). The token is minted only after the user clicks, handed
 * to the extension by same-origin postMessage, and never placed in a URL. The page loads no
 * third-party script (middleware CSP).
 */
function Pairing() {
  const { status } = useAuth();
  const router = useRouter();
  const back = safeReturn(useSearchParams().get("return"));
  const [phase, setPhase] = useState<Phase>("detecting");
  const [version, setVersion] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [manualToken, setManualToken] = useState<string | null>(null);
  const [userName, setUserName] = useState<string | null>(null);
  const [consented, setConsented] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (status === "signed-out") router.replace(`/signin?next=${encodeURIComponent("/connect/companion")}`);
  }, [status, router]);

  useEffect(() => {
    if (status !== "signed-in") return;
    api<{ purpose: string; given: boolean }[]>("/me/consents")
      .then((rows) => setConsented(rows.some((r) => r.purpose === "activity_sharing" && r.given)))
      .catch(() => undefined);
  }, [status]);

  useEffect(() => {
    function onMessage(ev: MessageEvent) {
      if (ev.source !== window || ev.origin !== window.location.origin) return;
      const data = ev.data as { type?: string; version?: string; ok?: boolean; userName?: string; error?: string };
      if (data?.type === "JINGLE_COMPANION_READY") {
        setVersion(data.version ?? null);
        setPhase((p) => (p === "detecting" || p === "missing" ? "ready" : p));
      } else if (data?.type === "JINGLE_COMPANION_PAIRED") {
        if (data.ok) {
          setUserName(data.userName ?? null);
          setPhase("paired");
        } else {
          setError(PAIR_ERRORS[data.error ?? ""] ?? PAIR_ERRORS.extension_error ?? null);
          setPhase("error");
        }
      }
    }
    window.addEventListener("message", onMessage);
    window.postMessage({ type: "JINGLE_COMPANION_PING" }, window.location.origin);
    timer.current = setTimeout(() => setPhase((p) => (p === "detecting" ? "missing" : p)), 3000);
    return () => {
      window.removeEventListener("message", onMessage);
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  async function mintToken(): Promise<string | null> {
    setError(null);
    try {
      if (consented) await api("/me/consents/activity_sharing", { method: "POST", ...json({ given: true }) });
      const res = await api<{ token: string }>("/sources/companion/token", { method: "POST" });
      return res.token;
    } catch (err) {
      if (err instanceof ApiError && err.code === "CONSENT_REQUIRED") {
        setPhase("consent");
        return null;
      }
      setError(err instanceof Error ? err.message : "That didn't work. Please try again in a moment.");
      setPhase("error");
      return null;
    }
  }

  async function connect() {
    setPhase("pairing");
    const token = await mintToken();
    if (!token) return;
    window.postMessage({ type: "JINGLE_COMPANION_TOKEN", token }, window.location.origin);
  }

  async function showManual() {
    const token = await mintToken();
    if (!token) return;
    setManualToken(token);
    setPhase("manual");
  }

  const needsConsent = phase === "consent";
  return (
    <div className="flex flex-col gap-5">
      <h1 className="font-display text-2xl font-semibold">Connect this browser</h1>
      {phase === "paired" ? (
        <div className="flex flex-col items-center gap-3 py-4 text-center" aria-live="polite">
          <Blip pose="cheer" size={96} decorative />
          <p className="font-display text-xl font-semibold">This browser is connected ✓</p>
          <p className="text-sm text-text-muted">
            {userName ? `Signed in as @${userName}. ` : ""}Play something in your music app&rsquo;s web player and friends
            will see it.
          </p>
          <Button onClick={() => router.push(back)}>Continue</Button>
        </div>
      ) : phase === "manual" && manualToken ? (
        <div className="flex flex-col gap-3">
          <p className="text-sm text-text-muted">
            Open the Jingle Companion and paste this code under &ldquo;Paste a token instead&rdquo;. It&rsquo;s shown once.
          </p>
          <code className="select-all break-all rounded-md bg-surface-2 p-3 font-mono text-sm">{manualToken}</code>
          <Button variant="secondary" onClick={() => router.push(back)}>
            I&rsquo;ve pasted it
          </Button>
        </div>
      ) : (
        <>
          <p className="text-sm text-text-muted">
            {phase === "detecting"
              ? "Looking for the Jingle Companion in this browser…"
              : phase === "missing"
                ? "We can't see the Jingle Companion in this browser yet. Install it, reload this page, and try again."
                : `Jingle Companion ${version ? `v${version} ` : ""}found. It shares only what you play in music web players, and only with your Jingle account.`}
          </p>
          {error && <FormAlert>{error}</FormAlert>}
          {(needsConsent || phase === "ready" || phase === "error" || phase === "missing") && (
            <label className="flex min-h-11 items-start gap-3 rounded-md border border-border p-3 text-sm">
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 accent-[var(--brand-violet)]"
                checked={consented}
                onChange={(e) => setConsented(e.target.checked)}
              />
              <span>
                Share what I play with my friends on Jingle. You can stop any time in Settings; stopping also erases the plays
                Jingle collected.
              </span>
            </label>
          )}
          <div className="flex flex-wrap gap-2">
            <Button onClick={connect} disabled={phase === "detecting" || phase === "missing" || !consented} loading={phase === "pairing"} loadingLabel="Connecting">
              Connect this browser
            </Button>
            {phase === "missing" && (
              <Button variant="secondary" onClick={showManual} disabled={!consented}>
                Show a code to paste instead
              </Button>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default function CompanionPairingPage() {
  return (
    <FocusShell>
      <Suspense>
        <Pairing />
      </Suspense>
    </FocusShell>
  );
}
