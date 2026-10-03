"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { Blip, Button } from "@/components/ds";
import { FocusShell } from "@/components/app/FocusShell";
import { api, json } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { detectExtension, pairExtension } from "@/lib/companion";

type Phase = "working" | "allow" | "done" | "missing" | "error";

function safeReturn(v: string | null): string {
  return v && v.startsWith("/") && !v.startsWith("//")
    ? v
    : "/settings/connections";
}

/**
 * Where the extension's own popup sends people (D-EXT-02). It connects by itself; the only
 * question it can ask is the one-tap "Allow" for sharing what you play. The token is minted
 * only on this page, handed over by same-origin postMessage, never placed in a URL.
 */
function Pairing() {
  const { status } = useAuth();
  const router = useRouter();
  const qc = useQueryClient();
  const back = safeReturn(useSearchParams().get("return"));
  const [phase, setPhase] = useState<Phase>("working");

  useEffect(() => {
    if (status === "signed-out")
      router.replace(
        `/signin?next=${encodeURIComponent("/connect/companion")}`,
      );
  }, [status, router]);

  const pair = useCallback(async () => {
    setPhase("working");
    if (!(await detectExtension(3000)).installed) return setPhase("missing");
    const r = await pairExtension();
    if (r.ok) {
      setPhase("done");
      void qc.invalidateQueries({ queryKey: ["connections"] });
      setTimeout(() => router.replace(back), 1500);
    } else setPhase(r.error === "CONSENT_REQUIRED" ? "allow" : "error");
  }, [qc, router, back]);

  useEffect(() => {
    if (status === "signed-in") void pair();
  }, [status, pair]);

  return (
    <div className="flex flex-col items-center gap-4 text-center" role="status">
      {phase === "working" && (
        <>
          <Blip size={48} />
          <h1 className="font-display text-2xl font-semibold">
            Connecting Jingle in Chrome…
          </h1>
        </>
      )}
      {phase === "done" && (
        <h1 className="font-display text-2xl font-semibold">
          Connected ✓ Play any song.
        </h1>
      )}
      {phase === "allow" && (
        <>
          <h1 className="font-display text-2xl font-semibold">
            Share what you play with your friends?
          </h1>
          <p className="text-sm text-text-muted">
            Stop any time in Settings → Privacy.
          </p>
          <Button
            variant="inverse"
            size="lg"
            onClick={async () => {
              await api("/me/consents/activity_sharing", {
                method: "POST",
                ...json({ given: true }),
              });
              await pair();
            }}
          >
            Allow
          </Button>
        </>
      )}
      {phase === "missing" && (
        <>
          <h1 className="font-display text-2xl font-semibold">
            Jingle isn&rsquo;t in this browser yet
          </h1>
          <Button variant="secondary" onClick={() => router.replace(back)}>
            Back to Jingle
          </Button>
        </>
      )}
      {phase === "error" && (
        <>
          <h1 className="font-display text-2xl font-semibold">
            That didn&rsquo;t connect
          </h1>
          <Button onClick={() => void pair()}>Try again</Button>
        </>
      )}
    </div>
  );
}

export default function CompanionPage() {
  return (
    <FocusShell>
      <Suspense>
        <Pairing />
      </Suspense>
    </FocusShell>
  );
}
