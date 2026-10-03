"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Button } from "@/components/ds";
import { api, json } from "@/lib/api";
import {
  detectExtension,
  onExtensionReady,
  pairExtension,
  type ExtensionState,
} from "@/lib/companion";

/**
 * Zero-setup extension (D-EXT-02). Once Jingle is added to Chrome, it connects itself to whoever is
 * signed in here: no settings, no codes. The only thing it may ever ask is the one-tap "Allow"
 * (sharing what you play needs your yes), shown once, as a small prompt.
 */
export function CompanionAutoPair() {
  const qc = useQueryClient();
  const [ask, setAsk] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let tried = false;
    const go = async (s: ExtensionState) => {
      if (tried || !s.installed || s.paired !== false) return;
      tried = true;
      const r = await pairExtension();
      if (r.ok) void qc.invalidateQueries({ queryKey: ["connections"] });
      else if (r.error === "CONSENT_REQUIRED") {
        try {
          if (sessionStorage.getItem("jingle-ext-allow") === "later") return;
        } catch {
          /* storage unavailable */
        }
        setAsk(true);
      }
    };
    const off = onExtensionReady((s) => void go(s));
    void detectExtension().then(go);
    return off;
  }, [qc]);

  if (!ask) return null;
  const allow = async () => {
    setBusy(true);
    try {
      await api("/me/consents/activity_sharing", {
        method: "POST",
        ...json({ given: true }),
      });
      const r = await pairExtension();
      if (r.ok) void qc.invalidateQueries({ queryKey: ["connections"] });
    } finally {
      setBusy(false);
      setAsk(false);
    }
  };
  const later = () => {
    try {
      sessionStorage.setItem("jingle-ext-allow", "later");
    } catch {
      /* ignore */
    }
    setAsk(false);
  };
  return (
    <div
      role="dialog"
      aria-labelledby="ext-allow-h"
      className="fixed inset-x-4 bottom-24 z-50 mx-auto flex max-w-md flex-col gap-3 rounded-[20px] border border-border bg-surface-1 p-5 shadow-xl md:bottom-6"
    >
      <p id="ext-allow-h" className="font-semibold">
        Let Jingle in Chrome share what you play?
      </p>
      <p className="text-sm text-text-muted">
        Your friends see the song you&rsquo;re on. Stop any time in Settings →
        Privacy.
      </p>
      <div className="flex gap-2">
        <Button variant="inverse" onClick={() => void allow()} disabled={busy}>
          Allow
        </Button>
        <Button variant="ghost" onClick={later}>
          Not now
        </Button>
      </div>
    </div>
  );
}
