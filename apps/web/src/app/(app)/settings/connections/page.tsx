"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { EmptyState, ErrorState, Icons, PlatformBadge, Skeleton } from "@/components/ds";
import { ConnectSheet, PLATFORMS, platformName, type MusicPlatform } from "@/components/app/Connect";
import { useConnections } from "@/lib/queries";

function rowStatus(status: string | undefined): string {
  switch (status) {
    case "CONNECTED":
      return "Connected";
    case "NEEDS_REAUTH":
      return "Needs reconnect";
    case "PENDING_FIRST_PLAY":
      return "Waiting for your first play";
    case "DISABLED":
      return "Paused";
    default:
      return "Not connected";
  }
}

/** Settings → Connections (UX_SPEC §5.14; BR-13–15). Route details and credits live here only. */
export default function ConnectionsSettingsPage() {
  const connections = useConnections();
  const qc = useQueryClient();
  const [open, setOpen] = useState<MusicPlatform | null>(null);

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Your music apps</h1>
      {connections.isLoading ? (
        <div className="flex flex-col gap-3">
          {PLATFORMS.map((p) => (
            <Skeleton key={p} className="h-24" rounded="lg" />
          ))}
        </div>
      ) : connections.isError ? (
        <ErrorState message="Couldn't load your connections." onRetry={() => void connections.refetch()} />
      ) : (
        <>
          {connections.data?.length === 0 && (
            <EmptyState pose="wave" title="No music apps connected." action={{ label: "Connect your music", onClick: () => setOpen("SPOTIFY") }} />
          )}
          <ul className="flex flex-col gap-3">
            {PLATFORMS.map((p) => {
              const c = connections.data?.find((x) => x.platform === p);
              return (
                <li key={p} className="flex flex-col gap-2 rounded-lg border border-border bg-surface-1 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-3">
                      <PlatformBadge platform={p} />
                      <span className="font-mono text-xs text-text-muted">{rowStatus(c?.status)}</span>
                    </div>
                    {c?.note && <p className="text-sm text-text-muted">{c.note}</p>}
                  </div>
                  <button
                    type="button"
                    onClick={() => setOpen(p)}
                    className="min-h-11 shrink-0 rounded-pill border border-border px-4 text-sm font-medium hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus-ring)]"
                  >
                    {c ? `Manage ${platformName(p)}` : `Connect ${platformName(p)}`}
                  </button>
                </li>
              );
            })}
          </ul>
        </>
      )}

      <details className="rounded-lg border border-border bg-surface-1 p-4 text-sm">
        <summary className="flex cursor-pointer items-center gap-2 font-medium">
          <Icons.Info size={16} /> How this works
        </summary>
        <div className="mt-3 flex flex-col gap-2 text-text-muted">
          <p>
            In your browser, the Jingle Companion notices what you play in the Spotify, Apple Music, YouTube Music and
            Amazon Music web players and shares it only with your Jingle account. Plays count as Live for 90 seconds after
            the last signal; after that they show with their real time.
          </p>
          <p>
            Phone listening: Spotify on any device and existing ListenBrainz or Last.fm accounts can be connected in the
            next update. Phone listening on Apple Music, YouTube Music and Amazon Music isn&rsquo;t shared in this version.
          </p>
          <p className="font-mono text-xs">
            Credits: track identification uses MusicBrainz; artwork from the Cover Art Archive. Last.fm data, when
            connected, is powered by AudioScrobbler.
          </p>
        </div>
      </details>

      <ConnectSheet
        platform={open}
        returnTo="/settings/connections"
        onClose={() => {
          setOpen(null);
          void qc.invalidateQueries({ queryKey: ["connections"] });
        }}
      />
    </div>
  );
}
