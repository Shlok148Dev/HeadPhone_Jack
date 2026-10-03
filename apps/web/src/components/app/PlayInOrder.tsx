"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Dialog, Icons, PlatformMark, buttonClasses, cn, type Platform } from "@/components/ds";
import { api, json } from "@/lib/api";
import type { PlaylistItem } from "@/lib/circles";
import { appleIdFromLink, openPopup, type ExportPlatform, type ExportResult, type ExportSong, type PriorExport } from "@/lib/exporters/common";

/**
 * "Play in order in your app" (JNG-04-09, D-EXPORT-01): Jingle builds (or updates) a copy of the
 * circle playlist inside your own Spotify, Apple Music or YouTube Music, in exactly this order, then
 * you open it there. Your app login happens in that app's own window and stays in this page.
 */
type Config = Record<ExportPlatform | "amazon_music", { enabled: boolean; client_id?: string | null; reason?: string }>;

const NAMES: Record<ExportPlatform | "amazon_music", string> = {
  spotify: "Spotify",
  apple_music: "Apple Music",
  youtube_music: "YouTube Music",
  amazon_music: "Amazon Music",
};
const MARK: Record<ExportPlatform | "amazon_music", Platform> = {
  spotify: "SPOTIFY",
  apple_music: "APPLE_MUSIC",
  youtube_music: "YOUTUBE_MUSIC",
  amazon_music: "AMAZON_MUSIC",
};
const FROM_PLATFORM: Partial<Record<Platform, ExportPlatform | "amazon_music">> = {
  SPOTIFY: "spotify",
  APPLE_MUSIC: "apple_music",
  YOUTUBE_MUSIC: "youtube_music",
  AMAZON_MUSIC: "amazon_music",
};

type State =
  | { kind: "idle" }
  | { kind: "working"; app: ExportPlatform; msg: string }
  | { kind: "done"; app: ExportPlatform; result: ExportResult }
  | { kind: "error"; app: ExportPlatform; msg: string }
  | { kind: "unavailable"; app: ExportPlatform | "amazon_music" };

export function PlayInOrder({ circleId, circleName, items, myPlatform }: { circleId: string; circleName: string; items: PlaylistItem[]; myPlatform?: Platform }) {
  const qc = useQueryClient();
  const config = useQuery({ queryKey: ["exports", "config"], queryFn: () => api<Config>("/exports/config"), staleTime: 10 * 60_000 });
  const priors = useQuery({ queryKey: ["circles", circleId, "exports"], queryFn: () => api<Record<string, PriorExport>>(`/circles/${circleId}/playlist/exports`) });
  const [state, setState] = useState<State>({ kind: "idle" });
  const [menu, setMenu] = useState(false);
  const primary: ExportPlatform | "amazon_music" = (myPlatform && FROM_PLATFORM[myPlatform]) || "spotify";
  const others = (["spotify", "apple_music", "youtube_music", "amazon_music"] as const).filter((p) => p !== primary);

  const songs: ExportSong[] = items.map((i) => ({ key: i.key, title: i.title, artist: i.artist, appleId: appleIdFromLink(i.links.APPLE_MUSIC) }));

  async function run(app: ExportPlatform | "amazon_music") {
    setMenu(false);
    const cfg = config.data?.[app];
    if (app === "amazon_music" || !cfg?.enabled) return setState({ kind: "unavailable", app });
    // Spotify's login popup must open inside this click, before any await.
    const popup = app === "spotify" ? openPopup("jingle-spotify") : null;
    const progress = (msg: string) => setState({ kind: "working", app, msg });
    progress(`Logging in to ${NAMES[app]}`);
    try {
      const prior = priors.data?.[app] ?? null;
      let result: ExportResult;
      if (app === "spotify") {
        const { spotifyLogin, exportToSpotify } = await import("@/lib/exporters/spotify");
        const token = await spotifyLogin(cfg.client_id!, popup);
        result = await exportToSpotify(token, circleName, songs, prior, progress);
      } else if (app === "youtube_music") {
        const { youtubeLogin, exportToYouTube } = await import("@/lib/exporters/youtube");
        const token = await youtubeLogin(cfg.client_id!);
        result = await exportToYouTube(token, circleId, circleName, songs, prior, progress);
      } else {
        const { appleLogin, exportToApple } = await import("@/lib/exporters/apple");
        const music = await appleLogin();
        result = await exportToApple(music, circleName, songs, prior, progress);
      }
      await api(`/circles/${circleId}/playlist/exports/${app}`, { method: "PUT", ...json({ external_id: result.externalId, url: result.url, track_keys: result.placedKeys }) });
      void qc.invalidateQueries({ queryKey: ["circles", circleId, "exports"] });
      setState({ kind: "done", app, result });
    } catch (e) {
      popup?.close();
      setState({ kind: "error", app, msg: e instanceof Error ? e.message : "Something went wrong." });
    }
  }

  const label = (app: ExportPlatform | "amazon_music") => `${priors.data?.[app as ExportPlatform] ? "Update & play" : "Play"} in ${NAMES[app]}`;
  const close = () => setState({ kind: "idle" });

  return (
    <div className="relative flex flex-wrap items-center gap-2">
      <Button variant="inverse" disabled={!items.length || config.isLoading} onClick={() => void run(primary)} leadingIcon={<PlatformMark platform={MARK[primary]} size={18} mono />}>
        {label(primary)}
      </Button>
      <Button variant="secondary" aria-expanded={menu} aria-haspopup="menu" onClick={() => setMenu((m) => !m)} disabled={!items.length}>
        Other apps
      </Button>
      {menu && (
        <ul role="menu" aria-label="Play in another app" className="absolute left-0 top-full z-30 mt-2 flex w-64 flex-col rounded-xl border border-border bg-surface-1 p-1 shadow-2">
          {others.map((p) => (
            <li key={p} role="none">
              <button role="menuitem" type="button" onClick={() => void run(p)} className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)]">
                <PlatformMark platform={MARK[p]} size={16} />
                {label(p)}
              </button>
            </li>
          ))}
        </ul>
      )}
      <p className="w-full text-xs text-text-muted">Makes a copy of this playlist in your app, in exactly this order. Run it again to bring your copy up to date.</p>

      <Dialog open={state.kind !== "idle"} onClose={close} title={dialogTitle(state)}>
        {state.kind === "working" && (
          <p className="flex items-center gap-3 text-sm" role="status">
            <span className="ds-spin inline-block h-4 w-4 rounded-full border-2 border-current border-t-transparent" aria-hidden />
            {state.msg}…
          </p>
        )}
        {state.kind === "done" && (
          <div className="flex flex-col gap-4">
            <p className="text-sm">
              {state.result.placedKeys.length} of {songs.length} songs are in your {NAMES[state.app]} playlist &ldquo;{circleName} · Jingle&rdquo;, in order.
            </p>
            {state.result.missing.length > 0 && (
              <div className="rounded-lg border border-border bg-surface-2 p-3 text-sm">
                <p className="font-medium">Not on {NAMES[state.app]}:</p>
                <ul className="mt-1 list-disc pl-5 text-text-muted">
                  {state.result.missing.slice(0, 8).map((s) => (
                    <li key={s.key}>
                      {s.title} · {s.artist}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {!!state.result.stale && (
              <p className="text-xs text-text-muted">
                {state.result.stale} {state.result.stale === 1 ? "song was" : "songs were"} removed from the circle; Apple Music doesn&rsquo;t let apps remove songs, so delete {state.result.stale === 1 ? "it" : "them"} in Apple Music if you like.
              </p>
            )}
            <a href={state.result.url} target="_blank" rel="noopener noreferrer" className={cn(buttonClasses("inverse", "lg", "gap-2"))}>
              <PlatformMark platform={MARK[state.app]} size={18} mono /> Open in {NAMES[state.app]}
            </a>
          </div>
        )}
        {state.kind === "error" && (
          <div className="flex flex-col gap-3">
            <p className="text-sm">{state.msg}</p>
            <Button variant="secondary" onClick={() => void run(state.app)}>
              Try again
            </Button>
          </div>
        )}
        {state.kind === "unavailable" && (
          <div className="flex flex-col gap-3 text-sm">
            <p>
              {state.app === "amazon_music"
                ? "Amazon Music doesn't let other apps create playlists, so Jingle can't make an in-order copy there."
                : `Playing in order on ${NAMES[state.app]} isn't switched on for this Jingle yet.`}
            </p>
            <p className="text-text-muted">Meanwhile, each song below has its own button to play it in your app.</p>
            <Button variant="secondary" onClick={close}>
              <Icons.Check size={16} /> Got it
            </Button>
          </div>
        )}
      </Dialog>
    </div>
  );
}

function dialogTitle(s: State): string {
  if (s.kind === "working") return `Building your ${NAMES[s.app]} playlist`;
  if (s.kind === "done") return `Ready in ${NAMES[s.app]}`;
  if (s.kind === "error") return `Couldn't finish in ${NAMES[s.app]}`;
  if (s.kind === "unavailable") return `Not available in ${NAMES[s.app]} yet`;
  return "";
}
