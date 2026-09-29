"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Button, Dialog, EmptyState, ErrorState, Icons, PlatformBadge, Skeleton, useToast } from "@/components/ds";
import { ConnectSheet, PLATFORMS, platformName, type MusicPlatform } from "@/components/app/Connect";
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
  spotify_not_available: "Spotify didn't let Jingle connect directly. You can still connect in your browser.",
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
  const [open, setOpen] = useState<MusicPlatform | null>(null);
  const [step, setStep] = useState<"link_spotify_lastfm" | undefined>();
  const [confirm, setConfirm] = useState<MusicPlatform | null>(null);

  // Returning from a platform's own consent screen (Spotify, Last.fm).
  useEffect(() => {
    const connected = params.get("connected");
    const error = params.get("error");
    if (!connected && !error) return;
    if (isPlatform(connected)) {
      toast.toast({ title: `${platformName(connected)} connected`, tone: "success" });
      if (params.get("then") === "link_spotify_lastfm") {
        setStep("link_spotify_lastfm");
        setOpen(connected);
      }
    } else if (error) {
      toast.toast({ title: RETURN_ERRORS[error] ?? "That didn't work. Try again.", tone: "danger" });
      const p = params.get("platform");
      if (isPlatform(p)) setOpen(p);
    }
    router.replace("/settings/connections");
    void qc.invalidateQueries({ queryKey: ["connections"] });
  }, [params, router, qc, toast]);

  const unlink = useMutation({
    mutationFn: (p: MusicPlatform) => api(`/connections/${p}`, { method: "DELETE" }),
    onSuccess: (_d, p) => {
      toast.toast({ title: `${platformName(p)} disconnected`, tone: "success" });
      void qc.invalidateQueries({ queryKey: ["connections"] });
      void qc.invalidateQueries({ queryKey: ["me", "card"] });
    },
    onError: () => toast.toast({ title: "Couldn't disconnect. Try again.", tone: "danger" }),
    onSettled: () => setConfirm(null),
  });

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
          {connections.data?.filter((c) => c.status !== "DISABLED").length === 0 && (
            <EmptyState pose="wave" title="No music apps connected." action={{ label: "Connect your music", onClick: () => setOpen("SPOTIFY") }} />
          )}
          <ul className="flex flex-col gap-3">
            {PLATFORMS.map((p) => {
              const c = connections.data?.find((x) => x.platform === p);
              const active = c && c.status !== "DISABLED";
              return (
                <li key={p} className="flex flex-col gap-3 rounded-lg border border-border bg-surface-1 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-3">
                      <PlatformBadge platform={p} />
                      <span className={`font-mono text-xs ${c?.status === "NEEDS_REAUTH" ? "text-warning" : "text-text-muted"}`}>
                        {rowStatus(c?.status)}
                      </span>
                    </div>
                    {c?.status === "NEEDS_REAUTH" && (
                      <p className="text-sm text-text">Jingle lost access to {platformName(p)}. Reconnect to keep your friends up to date.</p>
                    )}
                    {active && c.note && <p className="text-sm text-text-muted">{c.note}</p>}
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <Button variant={c?.status === "NEEDS_REAUTH" ? "primary" : "secondary"} onClick={() => setOpen(p)}>
                      {c?.status === "NEEDS_REAUTH" ? `Reconnect ${platformName(p)}` : active ? "Manage" : `Connect ${platformName(p)}`}
                    </Button>
                    {active && (
                      <Button variant="ghost" onClick={() => setConfirm(p)}>
                        Disconnect
                      </Button>
                    )}
                  </div>
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
            Amazon Music web players and shares it only with your Jingle account. For Spotify on your phone, Jingle reads
            Spotify&rsquo;s built-in Last.fm link, or connects to Spotify directly for a few testers. Existing ListenBrainz
            and Last.fm accounts work for any app. Plays count as Live for 90 seconds after the last signal; after that
            they show with their real time.
          </p>
          <p>Phone listening on Apple Music, YouTube Music and Amazon Music isn&rsquo;t shared in this version.</p>
          <p className="font-mono text-xs">
            Credits: Last.fm data powered by AudioScrobbler. Listening data from ListenBrainz (MetaBrainz Foundation).
            Track identification by MusicBrainz; artwork from the Cover Art Archive. Spotify data is shown with
            attribution and deleted when you disconnect Spotify.
          </p>
        </div>
      </details>

      <ConnectSheet
        platform={open}
        initialStep={step}
        returnTo="/settings/connections"
        onClose={() => {
          setOpen(null);
          setStep(undefined);
          void qc.invalidateQueries({ queryKey: ["connections"] });
        }}
      />
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
            <Button variant="danger" loading={unlink.isPending} loadingLabel="Disconnecting" onClick={() => confirm && unlink.mutate(confirm)}>
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
