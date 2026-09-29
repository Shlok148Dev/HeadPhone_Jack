"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { api, json, setAccessToken, type AuthPayload } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface Flags {
  google_signin_enabled: boolean;
  google_client_id: string;
}

interface GsiWindow extends Window {
  google?: {
    accounts: {
      id: {
        initialize: (cfg: { client_id: string; callback: (r: { credential: string }) => void }) => void;
        renderButton: (el: HTMLElement, opts: Record<string, unknown>) => void;
      };
    };
  };
}

export function useFlags() {
  return useQuery({ queryKey: ["flags"], queryFn: () => api<Flags & { flags: Record<string, boolean> }>("/flags") });
}

/**
 * "Continue with Google" rendered by Google Identity Services itself (Google's own button
 * guidelines). Hidden when no client id is configured — never a dead button (UX_SPEC §5.2).
 */
export function GoogleButton({ onSignedIn }: { onSignedIn: (created: boolean) => void }) {
  const flags = useFlags();
  const ref = useRef<HTMLDivElement>(null);
  const { setMe } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const clientId = flags.data?.google_signin_enabled ? flags.data.google_client_id : "";

  useEffect(() => {
    if (!clientId || !ref.current) return;
    const w = window as GsiWindow;
    const init = () => {
      if (!w.google || !ref.current) return;
      w.google.accounts.id.initialize({
        client_id: clientId,
        callback: async ({ credential }) => {
          try {
            const res = await api<AuthPayload & { created: boolean }>("/auth/google", {
              method: "POST",
              ...json({ id_token: credential }),
            });
            setAccessToken(res.access);
            setMe(res.user);
            onSignedIn(res.created);
            window.location.assign(res.user.needs_onboarding ? "/onboarding/profile" : "/home");
          } catch (e) {
            setError(e instanceof Error ? e.message : "Google sign-in isn't working right now. Use email instead.");
          }
        },
      });
      w.google.accounts.id.renderButton(ref.current, { theme: "filled_black", size: "large", width: 320, text: "continue_with" });
    };
    if (w.google) return init();
    const s = document.createElement("script");
    s.src = "https://accounts.google.com/gsi/client";
    s.async = true;
    s.onload = init;
    s.onerror = () => setError("Google sign-in isn't working right now. Use email instead.");
    document.head.appendChild(s);
  }, [clientId, onSignedIn, setMe]);

  if (!clientId) return null;
  return (
    <div className="flex flex-col items-center gap-2">
      {error && <p className="text-sm text-text-muted">{error}</p>}
      <div ref={ref} className="min-h-11" />
      <div className="flex w-full items-center gap-3 text-xs text-text-subtle" aria-hidden="true">
        <span className="h-px flex-1 bg-border" />
        or
        <span className="h-px flex-1 bg-border" />
      </div>
    </div>
  );
}
