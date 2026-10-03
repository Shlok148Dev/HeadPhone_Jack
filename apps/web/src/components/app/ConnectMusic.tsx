"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import {
  Button,
  Icons,
  PlatformMark,
  buttonClasses,
  cn,
} from "@/components/ds";
import { api, ApiError, json } from "@/lib/api";
import {
  androidBridge,
  canRunExtension,
  detectExtension,
  isAndroid,
  isPhone,
  onExtensionReady,
  pairAndroid,
  pairExtension,
} from "@/lib/companion";
import { useConnections, type Connection } from "@/lib/queries";
import { PLATFORMS, platformName, type MusicPlatform } from "./Connect";

/**
 * One-tap Connect (D-CONNECT-01). Four buttons; pressing one is the whole job. Under the hood the
 * server picks the route per person, and the listener only ever sees their music app's own login:
 * - Spotify: Spotify's login (25 direct slots), otherwise Last.fm's login + one tap inside Last.fm.
 * - Apple Music: Apple's sign-in (when Jingle has Apple keys), otherwise the extension.
 * - YouTube Music / Amazon Music: desktop → "Add to Chrome" (the extension connects itself);
 *   Android → the Jingle app; iPhone → not possible (Apple doesn't allow it), said plainly.
 */
const APPS = PLATFORMS.map((id) => ({ id, name: platformName(id) }));
type Plan = {
  action: "redirect" | "lastfm_then_spotify" | "browser" | "musickit";
  url: string | null;
};
type Step =
  | { kind: "idle" }
  | { kind: "working"; app: MusicPlatform; msg: string }
  | { kind: "add-extension"; app: MusicPlatform; storeUrl: string | null }
  | { kind: "get-app"; app: MusicPlatform; androidUrl: string | null }
  | { kind: "iphone"; app: MusicPlatform }
  | { kind: "other-browser"; app: MusicPlatform }
  | { kind: "error"; app: MusicPlatform; msg: string };

/** Where to land after Spotify's/Last.fm's login (their callbacks go to Settings → Connections). */
export const RETURN_KEY = "jingle-connect-return";
const LASTFM_APPS_URL = "https://www.last.fm/settings/applications";

export function ConnectMusic({ compact = false }: { compact?: boolean }) {
  const qc = useQueryClient();
  const conns = useConnections({ poll: true });
  const cfg = useQuery({
    queryKey: ["connect-config"],
    queryFn: () =>
      api<{ extension_url: string | null; android_url: string | null }>(
        "/sources/connect-config",
      ),
    staleTime: 10 * 60_000,
  });
  const [step, setStep] = useState<Step>({ kind: "idle" });
  // Back from Last.fm's login: one tap left, inside Last.fm. We finish on the first song.
  const [lastfmLink, setLastfmLink] = useState(false);
  const busy = useRef(false);
  // Jingle in Chrome is connected; the tile flips to Connected on the first song it sees there.
  const [waiting, setWaiting] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    if (p.get("then") === "link_spotify_lastfm") setLastfmLink(true);
    if (p.get("connected") || p.get("then"))
      void qc.invalidateQueries({ queryKey: ["connections"] });
  }, [qc]);

  const status = (id: MusicPlatform): Connection | undefined =>
    conns.data?.find((c) => c.platform === id);
  const refresh = () =>
    void qc.invalidateQueries({ queryKey: ["connections"] });

  async function viaExtension(app: MusicPlatform) {
    if (androidBridge()) return viaAndroidApp(app);
    if (isPhone())
      return setStep(
        isAndroid()
          ? { kind: "get-app", app, androidUrl: cfg.data?.android_url ?? null }
          : { kind: "iphone", app },
      );
    if (!canRunExtension()) return setStep({ kind: "other-browser", app });
    setStep({ kind: "working", app, msg: "Checking for Jingle in Chrome" });
    const ext = await detectExtension();
    if (ext.installed) return finishPairing(app);
    setStep({
      kind: "add-extension",
      app,
      storeUrl: cfg.data?.extension_url ?? null,
    });
  }

  // In the Android app: one toggle in Android's settings; the tile then waits for the first song.
  async function viaAndroidApp(app: MusicPlatform) {
    setStep({ kind: "working", app, msg: "Connecting" });
    const r = await pairAndroid();
    if (!r.ok)
      return setStep({
        kind: "error",
        app,
        msg: "Couldn't connect. Try again.",
      });
    refresh();
    setWaiting((w) => new Set(w).add(app));
    setStep({ kind: "idle" });
  }

  async function finishPairing(app: MusicPlatform) {
    setStep({ kind: "working", app, msg: "Connecting" });
    const r = await pairExtension();
    if (r.ok) {
      refresh();
      setWaiting((w) => new Set(w).add(app));
      setStep({ kind: "idle" });
    } else
      setStep({
        kind: "error",
        app,
        msg: "Jingle in Chrome couldn't connect. Try again.",
      });
  }

  // While "Add to Chrome" is open, the extension announces itself the moment it's installed.
  useEffect(() => {
    if (step.kind !== "add-extension") return;
    const app = step.app;
    return onExtensionReady((s) => {
      if (s.installed) void finishPairing(app);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step.kind]);

  async function connect(app: MusicPlatform) {
    if (busy.current) return;
    busy.current = true;
    setStep({ kind: "working", app, msg: "Opening" });
    try {
      // In the Android app every music app is read on the phone itself (live; no other login).
      if (androidBridge()) {
        await api(`/sources/${app}/connect`, {
          method: "POST",
          ...json({ consent: true }),
        }); // records the consent
        return await viaAndroidApp(app);
      }
      // Pressing the button is the consent (the notice sits right under the buttons).
      const plan = await api<Plan>(`/sources/${app}/connect`, {
        method: "POST",
        ...json({ consent: true }),
      });
      if (
        (plan.action === "redirect" || plan.action === "lastfm_then_spotify") &&
        plan.url
      ) {
        try {
          sessionStorage.setItem(RETURN_KEY, window.location.pathname); // come back to this screen
        } catch {
          /* storage unavailable: lands in Settings → Connections */
        }
        window.location.assign(plan.url); // the app's own login, then straight back here
        return;
      }
      if (plan.action === "musickit") {
        setStep({ kind: "working", app, msg: "Signing in to Apple Music" });
        const { appleMusicUserToken } = await import("@/lib/exporters/apple");
        const token = await appleMusicUserToken();
        await api("/sources/apple/link", {
          method: "POST",
          ...json({ music_user_token: token }),
        });
        refresh();
        setStep({ kind: "idle" });
        return;
      }
      await viaExtension(app);
    } catch (e) {
      setStep({
        kind: "error",
        app,
        msg:
          e instanceof ApiError
            ? e.message
            : e instanceof Error
              ? e.message
              : "Couldn't connect.",
      });
    } finally {
      busy.current = false;
    }
  }

  const spotifyDone = status("SPOTIFY")?.status === "CONNECTED";
  const name = (id: MusicPlatform) => APPS.find((a) => a.id === id)!.name;

  return (
    <section aria-labelledby="connect-h" className="flex flex-col gap-4">
      <h2
        id="connect-h"
        className={cn(
          "font-display font-semibold tracking-tight",
          compact ? "text-xl" : "text-2xl md:text-3xl",
        )}
      >
        Connect your music
      </h2>

      {lastfmLink && !spotifyDone && (
        <div
          className="flex flex-col gap-3 rounded-[20px] border border-border bg-surface-1 p-5"
          role="status"
        >
          <p className="font-semibold">
            One last tap: connect Spotify inside Last.fm
          </p>
          <p className="text-sm text-text-muted">
            Last.fm opens on its Applications page. Press <b>Connect</b> next to
            Spotify. That&rsquo;s it: play any song and Jingle finishes on its
            own.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <a
              href={LASTFM_APPS_URL}
              target="_blank"
              rel="noopener noreferrer"
              className={buttonClasses("inverse", "md", "gap-2")}
            >
              <PlatformMark platform="SPOTIFY" size={16} mono /> Open Last.fm
            </a>
            <span className="inline-flex items-center gap-2 font-mono text-xs text-text-muted">
              <span
                aria-hidden
                className="ds-spin inline-block h-3 w-3 rounded-full border-2 border-current border-t-transparent"
              />
              Waiting for your first song
            </span>
          </div>
        </div>
      )}

      <ul
        className="grid grid-cols-1 gap-3 sm:grid-cols-2"
        aria-label="Music apps"
      >
        {APPS.map((a) => {
          const c = status(a.id);
          const working = step.kind === "working" && step.app === a.id;
          const label =
            c?.status === "CONNECTED"
              ? "Connected"
              : c?.status === "PENDING_FIRST_PLAY"
                ? "Play a song to finish"
                : waiting.has(a.id)
                  ? `Play a song on ${a.name} to finish`
                  : c?.status === "NEEDS_REAUTH"
                    ? `Log in again to ${a.name}`
                    : null;
          return (
            <li key={a.id}>
              <button
                type="button"
                disabled={working || c?.status === "CONNECTED"}
                onClick={() => void connect(a.id)}
                className="group flex w-full items-center gap-4 rounded-[20px] border border-border bg-surface-1 p-4 text-left transition-colors hover:border-border-strong hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)] disabled:cursor-default disabled:hover:bg-surface-1"
              >
                <span className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-surface-2">
                  <PlatformMark
                    platform={a.id}
                    size={26}
                    className={
                      a.id === "AMAZON_MUSIC" ? "h-auto w-[38px]" : undefined
                    }
                  />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block font-semibold">{a.name}</span>
                  <span
                    className={cn(
                      "block truncate text-sm",
                      c?.status === "CONNECTED"
                        ? "text-success"
                        : "text-text-muted",
                    )}
                  >
                    {working
                      ? `${(step as { msg: string }).msg}…`
                      : (label ?? `Log in with ${a.name}`)}
                  </span>
                </span>
                {c?.status === "CONNECTED" ? (
                  <Icons.Check size={20} className="text-success" />
                ) : (
                  <Icons.ChevronRight
                    size={18}
                    className="text-text-muted group-hover:text-text"
                  />
                )}
              </button>
            </li>
          );
        })}
      </ul>
      <p className="text-xs text-text-muted">
        Connecting shows your friends what you play. You can stop any time in
        Settings → Privacy.
      </p>

      {step.kind === "add-extension" && (
        <div
          className="flex flex-col gap-3 rounded-[20px] border border-border bg-surface-1 p-5"
          role="status"
        >
          <p className="font-semibold">
            Add Jingle to Chrome to connect {name(step.app)}
          </p>
          {step.storeUrl ? (
            <>
              <p className="text-sm text-text-muted">
                Click <b>Add to Chrome</b>, then <b>Add extension</b>. Jingle
                connects itself; nothing else to do.
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <a
                  href={step.storeUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={buttonClasses("inverse", "md")}
                >
                  Add Jingle to Chrome
                </a>
                <span className="inline-flex items-center gap-2 font-mono text-xs text-text-muted">
                  <span
                    aria-hidden
                    className="ds-spin inline-block h-3 w-3 rounded-full border-2 border-current border-t-transparent"
                  />
                  Waiting for Chrome
                </span>
              </div>
            </>
          ) : (
            <p className="text-sm text-text-muted">
              The Jingle extension isn&rsquo;t on the Chrome Web Store yet.
              (Developers: load{" "}
              <code className="font-mono">apps/companion-extension/dist</code>{" "}
              in <code className="font-mono">chrome://extensions</code>; it
              connects itself.)
            </p>
          )}
        </div>
      )}
      {step.kind === "get-app" && (
        <div
          className="rounded-[20px] border border-border bg-surface-1 p-5"
          role="status"
        >
          <p className="font-semibold">
            {name(step.app)} on your phone goes through the Jingle app
          </p>
          {step.androidUrl ? (
            <a
              href={step.androidUrl}
              className={cn(buttonClasses("inverse", "md"), "mt-3")}
            >
              Get the Jingle app
            </a>
          ) : (
            <p className="mt-1 text-sm text-text-muted">
              The Jingle Android app is on its way. On a computer, connect it
              with Chrome in one tap.
            </p>
          )}
        </div>
      )}
      {step.kind === "iphone" && (
        <p
          className="rounded-[20px] border border-border bg-surface-1 p-5 text-sm"
          role="status"
        >
          iPhones don&rsquo;t let any app see what {name(step.app)} is playing.
          Connect it from Chrome on a computer, or with the Jingle Android app.
        </p>
      )}
      {step.kind === "other-browser" && (
        <p
          className="rounded-[20px] border border-border bg-surface-1 p-5 text-sm"
          role="status"
        >
          Open Jingle in Chrome or Edge on a computer to connect{" "}
          {name(step.app)} in one tap.
        </p>
      )}
      {step.kind === "error" && (
        <div
          className="flex flex-wrap items-center gap-3 rounded-[20px] border border-border bg-surface-1 p-4"
          role="alert"
        >
          <p className="text-sm">{step.msg}</p>
          <Button variant="secondary" onClick={() => void connect(step.app)}>
            Try again
          </Button>
        </div>
      )}
    </section>
  );
}
