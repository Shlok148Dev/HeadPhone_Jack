"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import {
  Button,
  Dialog,
  ErrorState,
  Icons,
  PlatformBadge,
  Skeleton,
  useToast,
} from "@/components/ds";
import {
  PLATFORMS,
  platformName,
  type MusicPlatform,
} from "@/components/app/Connect";
import { ConnectMusic, RETURN_KEY } from "@/components/app/ConnectMusic";
import { api } from "@/lib/api";
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
      return "Disconnected";
    default:
      return "Not connected";
  }
}

const RETURN_ERRORS: Record<string, string> = {
  cancelled: "Connecting was cancelled. You can try again any time.",
  spotify_not_available:
    "Spotify didn't let Jingle connect directly. You can still connect in your browser.",
  connect_expired: "That took too long. Please try connecting again.",
  lastfm_failed: "We couldn't connect Last.fm. Try again.",
};

function isPlatform(v: string | null): v is MusicPlatform {
  return !!v && (PLATFORMS as string[]).includes(v);
}

/** Settings → Connections (UX_SPEC §5.14; BR-13–15, JNG-01-09, JNG-01-11). Credits live here only. */
function Connections() {
  const connections = useConnections();
  const qc = useQueryClient();
  const toast = useToast();
  const router = useRouter();
  const params = useSearchParams();
  const [confirm, setConfirm] = useState<MusicPlatform | null>(null);

  // Returning from a platform's own login (Spotify, Last.fm): say so, then tidy the URL.
  useEffect(() => {
    const connected = params.get("connected");
    const error = params.get("error");
    if (!connected && !error) return;
    let back: string | null = null;
    try {
      back = sessionStorage.getItem(RETURN_KEY);
      sessionStorage.removeItem(RETURN_KEY);
    } catch {
      /* storage unavailable */
    }
    if (
      back &&
      back.startsWith("/") &&
      !back.startsWith("//") &&
      back !== "/settings/connections"
    ) {
      router.replace(`${back}?${params.toString()}`); // finish where they started (e.g. onboarding)
      return;
    }
    if (isPlatform(connected) && params.get("then") !== "link_spotify_lastfm")
      toast.toast({
        title: `${platformName(connected)} connected`,
        tone: "success",
      });
    else if (error)
      toast.toast({
        title: RETURN_ERRORS[error] ?? "That didn't work. Try again.",
        tone: "danger",
      });
    if (params.get("then") !== "link_spotify_lastfm")
      router.replace("/settings/connections");
    void qc.invalidateQueries({ queryKey: ["connections"] });
  }, [params, router, qc, toast]);

  const unlink = useMutation({
    mutationFn: (p: MusicPlatform) =>
      api(`/connections/${p}`, { method: "DELETE" }),
    onSuccess: (_d, p) => {
      toast.toast({
        title: `${platformName(p)} disconnected`,
        tone: "success",
      });
      void qc.invalidateQueries({ queryKey: ["connections"] });
      void qc.invalidateQueries({ queryKey: ["me", "card"] });
    },
    onError: () =>
      toast.toast({ title: "Couldn't disconnect. Try again.", tone: "danger" }),
    onSettled: () => setConfirm(null),
  });

  const active = (connections.data ?? []).filter(
    (c) => c.status !== "DISABLED" && isPlatform(c.platform),
  );
  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <h1 className="font-display text-3xl font-semibold tracking-tight">
        Your music apps
      </h1>
      {connections.isError ? (
        <ErrorState
          message="Couldn't load your connections."
          onRetry={() => void connections.refetch()}
        />
      ) : connections.isLoading ? (
        <Skeleton className="h-48" rounded="lg" />
      ) : (
        <ConnectMusic compact />
      )}
      {active.length > 0 && (
        <ul className="flex flex-col gap-2" aria-label="Connected apps">
          {active.map((c) => {
            const p = c.platform as MusicPlatform;
            return (
              <li
                key={p}
                className="flex items-center justify-between gap-3 rounded-lg border border-border bg-surface-1 px-4 py-3"
              >
                <div className="flex min-w-0 flex-col gap-0.5">
                  <div className="flex items-center gap-3">
                    <PlatformBadge platform={p} />
                    <span
                      className={`font-mono text-xs ${c.status === "NEEDS_REAUTH" ? "text-warning" : "text-text-muted"}`}
                    >
                      {rowStatus(c.status)}
                    </span>
                  </div>
                  {c.note && (
                    <p className="text-sm text-text-muted">{c.note}</p>
                  )}
                </div>
                <Button variant="ghost" onClick={() => setConfirm(p)}>
                  Disconnect
                </Button>
              </li>
            );
          })}
        </ul>
      )}

      <details className="rounded-lg border border-border bg-surface-1 p-4 text-sm">
        <summary className="flex cursor-pointer items-center gap-2 font-medium">
          <Icons.Info size={16} /> How this works
        </summary>
        <div className="mt-3 flex flex-col gap-2 text-text-muted">
          <p>
            Spotify connects through Spotify&rsquo;s own login (or, while
            Spotify limits new apps, through Last.fm&rsquo;s login and
            Spotify&rsquo;s built-in Last.fm link), so it works from the Spotify
            app on any device. Apple Music connects with Apple&rsquo;s sign-in.
            YouTube Music and Amazon Music connect through Jingle in Chrome on a
            computer, or the Jingle app on Android. Plays count as Live for 90
            seconds after the last signal; after that they show with their real
            time.
          </p>
          <p className="font-mono text-xs">
            Credits: Last.fm data powered by AudioScrobbler. Listening data from
            ListenBrainz (MetaBrainz Foundation). Track identification by
            MusicBrainz; artwork from the Cover Art Archive. Spotify data is
            shown with attribution and deleted when you disconnect Spotify.
          </p>
        </div>
      </details>

      <Dialog
        open={confirm !== null}
        onClose={() => setConfirm(null)}
        title={confirm ? `Disconnect ${platformName(confirm)}?` : ""}
        description={
          confirm === "SPOTIFY"
            ? "Friends stop seeing what you play on Spotify. Data Jingle got directly from Spotify is deleted now. Your other apps keep working."
            : "Friends stop seeing what you play there. Your other apps keep working, and your past plays stay in your history."
        }
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirm(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              loading={unlink.isPending}
              loadingLabel="Disconnecting"
              onClick={() => confirm && unlink.mutate(confirm)}
            >
              Disconnect
            </Button>
          </>
        }
      />
    </div>
  );
}

export default function ConnectionsSettingsPage() {
  return (
    <Suspense>
      <Connections />
    </Suspense>
  );
}
