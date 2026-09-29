"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Blip, Button, ButtonLink, Icons, PlatformBadge, Sheet, Skeleton, cn, type Platform } from "@/components/ds";
import { ApiError, api, json } from "@/lib/api";
import { useConnections, type Connection } from "@/lib/queries";
import { FormAlert, TextField } from "./forms";

export type MusicPlatform = Exclude<Platform, "UNKNOWN">;

export const PLATFORMS: MusicPlatform[] = ["SPOTIFY", "APPLE_MUSIC", "YOUTUBE_MUSIC", "AMAZON_MUSIC"];

const NAMES: Record<MusicPlatform, string> = {
  SPOTIFY: "Spotify",
  APPLE_MUSIC: "Apple Music",
  YOUTUBE_MUSIC: "YouTube Music",
  AMAZON_MUSIC: "Amazon Music",
};

const WEB_PLAYER: Record<MusicPlatform, string> = {
  SPOTIFY: "https://open.spotify.com",
  APPLE_MUSIC: "https://music.apple.com",
  YOUTUBE_MUSIC: "https://music.youtube.com",
  AMAZON_MUSIC: "https://music.amazon.com",
};

/** Honest capability lines (UX_SPEC §10, web-phase pilot). */
const CAPABILITY: Record<MusicPlatform, { line: string; promise: string }> = {
  SPOTIFY: {
    line: "Live in your browser",
    promise: "Friends see you live when you play, on your phone or computer.",
  },
  APPLE_MUSIC: {
    line: "Live in your browser",
    promise: "You'll show as live when you play in your browser. Phone listening on Apple Music isn't shared yet.",
  },
  YOUTUBE_MUSIC: {
    line: "Live in your browser · history by import",
    promise:
      "You'll show as live when you play in your browser. Phone listening on YouTube Music shows up after you import your history.",
  },
  AMAZON_MUSIC: {
    line: "Live in your browser",
    promise: "You'll show as live when you play in your browser. Phone listening on Amazon Music doesn't show yet.",
  },
};

interface Plan {
  action: "redirect" | "lastfm_then_spotify" | "browser";
  url: string | null;
  live_on_phone: boolean;
}

const CONSENT_COPY: Record<string, string> = {
  activity_sharing: "Share what I play with my friends on Jingle. I can stop any time in Settings; stopping erases the plays Jingle collected.",
  lastfm_link: "Let Jingle read what I play from my Last.fm account. I can stop any time in Settings.",
};

export function platformName(p: MusicPlatform): string {
  return NAMES[p];
}

function statusText(c: Connection | undefined): string | null {
  if (!c) return null;
  if (c.status === "CONNECTED") return "Connected ✓";
  if (c.status === "NEEDS_REAUTH") return "Needs reconnect";
  if (c.status === "PENDING_FIRST_PLAY") return "Waiting for your first play";
  return null;
}

export function ConnectPlatformCard({
  platform,
  connection,
  primary,
  onConnect,
}: {
  platform: MusicPlatform;
  connection?: Connection;
  primary?: boolean;
  onConnect: (p: MusicPlatform) => void;
}) {
  const status = statusText(connection);
  const connected = connection?.status === "CONNECTED";
  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-lg border bg-surface-2 p-4 transition-colors",
        primary
          ? "border-2 border-transparent [background:linear-gradient(var(--surface-2),var(--surface-2))_padding-box,var(--gradient-brand)_border-box]"
          : "border-border",
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <PlatformBadge platform={platform} />
        {status && <span className="font-mono text-xs text-text-muted">{status}</span>}
      </div>
      <p className="text-sm text-text-muted">
        {platform === "SPOTIFY" && connection?.capabilities.live_on_phone ? "Live on any device" : CAPABILITY[platform].line}
      </p>
      <Button variant={primary && !connected ? "primary" : "secondary"} onClick={() => onConnect(platform)}>
        {connection?.status === "NEEDS_REAUTH"
          ? `Reconnect ${NAMES[platform]}`
          : connected
            ? `Manage ${NAMES[platform]}`
            : `Connect ${NAMES[platform]}`}
      </Button>
    </div>
  );
}

function ConsentBox({ purpose, onGiven }: { purpose: string; onGiven: () => void }) {
  const [checked, setChecked] = useState(false);
  const give = useMutation({
    mutationFn: () => api(`/me/consents/${purpose}`, { method: "POST", ...json({ given: true }) }),
    onSuccess: onGiven,
  });
  return (
    <div className="flex flex-col gap-3 rounded-md border border-border p-3">
      <label className="flex min-h-11 items-start gap-3 text-sm">
        <input type="checkbox" className="mt-0.5 h-4 w-4 accent-[var(--brand-violet)]" checked={checked} onChange={(e) => setChecked(e.target.checked)} />
        <span>{CONSENT_COPY[purpose] ?? "Allow this to continue."}</span>
      </label>
      <Button disabled={!checked} loading={give.isPending} loadingLabel="Saving" onClick={() => give.mutate()}>
        Continue
      </Button>
    </div>
  );
}

function BrowserSteps({ platform, returnTo, slow }: { platform: MusicPlatform; returnTo: string; slow: boolean }) {
  const name = NAMES[platform];
  return (
    <>
      <li className="flex flex-col gap-2">
        <p className="font-medium">Install the Jingle Companion for your browser</p>
        <p className="text-sm text-text-muted">
          It notices what you play in {name}&rsquo;s web player and shares it only with your Jingle account. For the pilot,
          install it from the file your Jingle host gave you (Chrome or Edge: Extensions → Developer mode → Load unpacked).
        </p>
        <ButtonLink href={`/connect/companion?return=${encodeURIComponent(returnTo)}`} variant="secondary" leadingIcon={<Icons.Plug size={18} />}>
          Connect this browser
        </ButtonLink>
      </li>
      <li className="flex flex-col gap-2">
        <p className="font-medium">Play any song in {name} now</p>
        <a
          href={WEB_PLAYER[platform]}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-sm font-medium text-accent-text underline-offset-4 hover:underline"
        >
          Open {name} in a new tab <Icons.Open size={14} />
        </a>
        <div className="flex items-center gap-3 rounded-md bg-surface-2 p-3" aria-live="polite">
          <Blip pose="idle" size={40} decorative />
          <p className="text-sm text-text-muted">
            {slow ? `No play yet. Make sure ${name} is playing, then try again.` : "Listening for your first play…"}
          </p>
        </div>
      </li>
    </>
  );
}

function ListenBrainzForm({ platform }: { platform: MusicPlatform }) {
  const qc = useQueryClient();
  const [token, setToken] = useState("");
  const link = useMutation({
    mutationFn: () => api("/sources/listenbrainz", { method: "POST", ...json({ platform, token }) }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["connections"] }),
  });
  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(e: FormEvent) => {
        e.preventDefault();
        link.mutate();
      }}
    >
      <TextField
        label="ListenBrainz user token"
        hint="From listenbrainz.org → Settings. Already scrobbling there? Jingle picks it up."
        value={token}
        onChange={(e) => setToken(e.target.value)}
        error={link.error instanceof ApiError ? link.error.message : undefined}
        autoComplete="off"
      />
      {link.isSuccess ? (
        <p className="text-sm text-success">Connected ✓</p>
      ) : (
        <Button type="submit" variant="secondary" loading={link.isPending} loadingLabel="Connecting" disabled={!token.trim()}>
          Connect
        </Button>
      )}
    </form>
  );
}

function LastfmForm({ platform }: { platform: MusicPlatform }) {
  const qc = useQueryClient();
  const [username, setUsername] = useState("");
  const [consentNeeded, setConsentNeeded] = useState<string | null>(null);
  const link = useMutation({
    mutationFn: () => api("/sources/lastfm/username", { method: "POST", ...json({ platform, username }) }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["connections"] }),
    onError: (e) => {
      if (e instanceof ApiError && e.code === "CONSENT_REQUIRED") setConsentNeeded(String(e.details.purpose ?? "lastfm_link"));
    },
  });
  if (consentNeeded) return <ConsentBox purpose={consentNeeded} onGiven={() => { setConsentNeeded(null); link.mutate(); }} />;
  return (
    <form className="flex flex-col gap-2" onSubmit={(e: FormEvent) => { e.preventDefault(); link.mutate(); }}>
      <TextField
        label="Last.fm username"
        hint="Your Last.fm profile must be public."
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        error={link.error instanceof ApiError && link.error.code !== "CONSENT_REQUIRED" ? link.error.message : undefined}
        autoComplete="off"
      />
      {link.isSuccess ? (
        <p className="text-sm text-success">Connected ✓</p>
      ) : (
        <Button type="submit" variant="secondary" loading={link.isPending} loadingLabel="Connecting" disabled={!username.trim()}>
          Connect
        </Button>
      )}
    </form>
  );
}

interface ImportStatus {
  status: "queued" | "processing" | "done" | "failed";
  imported: number;
  found?: number;
  error?: string;
}

function TakeoutUpload() {
  const qc = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const [job, setJob] = useState<string | null>(null);
  const upload = useMutation({
    mutationFn: async (file: File) => {
      const body = new FormData();
      body.append("file", file);
      return api<{ job_id: string }>("/imports/youtube", { method: "POST", body });
    },
    onSuccess: (r) => setJob(r.job_id),
  });
  const status = useQuery({
    queryKey: ["import", job],
    queryFn: () => api<ImportStatus>(`/imports/${job}`),
    enabled: !!job,
    refetchInterval: (q) => (q.state.data && ["done", "failed"].includes(q.state.data.status) ? false : 1500),
  });
  useEffect(() => {
    if (status.data?.status === "done") void qc.invalidateQueries({ queryKey: ["connections"] });
  }, [status.data?.status, qc]);
  const s = status.data;
  return (
    <div className="flex flex-col gap-2 text-sm">
      <p className="text-text-muted">
        In Google Takeout, choose YouTube and YouTube Music → history, format JSON (HTML works too). Upload{" "}
        <span className="font-mono">watch-history.json</span> here. Files up to 50 MB; we delete it right after reading.
      </p>
      <input
        ref={input}
        type="file"
        accept=".json,.html,application/json,text/html"
        className="sr-only"
        aria-label="Choose your watch history file"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) upload.mutate(f);
        }}
      />
      {upload.error && <FormAlert>{upload.error.message}</FormAlert>}
      {s?.status === "done" ? (
        <p className="text-success">Imported {s.imported} plays from YouTube Music ✓</p>
      ) : s?.status === "failed" ? (
        <FormAlert>{s.error}</FormAlert>
      ) : job ? (
        <p aria-live="polite" className="text-text-muted">Reading your history… {s?.imported ? `${s.imported} plays so far` : ""}</p>
      ) : (
        <Button variant="secondary" loading={upload.isPending} loadingLabel="Uploading" onClick={() => input.current?.click()}>
          Upload your history file
        </Button>
      )}
    </div>
  );
}

/**
 * Connect sheet (BR-13): one flow per platform; the Connection Orchestrator picks the route and the
 * user only sees each platform's own consent screen. Route names appear only under
 * "Other ways to connect", the one place the UX spec allows them.
 */
export function ConnectSheet({
  platform,
  onClose,
  returnTo,
  initialStep,
}: {
  platform: MusicPlatform | null;
  onClose: () => void;
  returnTo: string;
  initialStep?: "link_spotify_lastfm";
}) {
  const connections = useConnections({ poll: platform !== null });
  const conn = connections.data?.find((c) => c.platform === platform);
  const [consent, setConsent] = useState<string | null>(null);
  const [slow, setSlow] = useState(false);
  const plan = useMutation({
    mutationFn: (p: MusicPlatform) => api<Plan>(`/sources/${p}/connect`, { method: "POST" }),
    onError: (e) => {
      if (e instanceof ApiError && e.code === "CONSENT_REQUIRED") setConsent(String(e.details.purpose ?? "activity_sharing"));
    },
  });
  const { mutate } = plan;

  useEffect(() => {
    if (!platform) return;
    setConsent(null);
    setSlow(false);
    mutate(platform);
    const t = setTimeout(() => setSlow(true), 120_000);
    return () => clearTimeout(t);
  }, [platform, mutate]);

  if (!platform) return <Sheet open={false} onClose={onClose} title="" />;
  const name = NAMES[platform];
  const done = conn?.status === "CONNECTED" && conn.first_play_at;
  const p = plan.data;

  let body;
  if (consent) {
    body = <ConsentBox purpose={consent} onGiven={() => { setConsent(null); mutate(platform); }} />;
  } else if (plan.isPending || (!p && !plan.isError)) {
    body = <Skeleton className="h-40" rounded="lg" />;
  } else if (plan.isError) {
    body = (
      <div className="flex flex-col gap-3">
        <FormAlert>{`We couldn't connect ${name}. Try again, or use another way to connect.`}</FormAlert>
        <Button variant="secondary" onClick={() => mutate(platform)}>Try again</Button>
      </div>
    );
  } else if (done && initialStep !== "link_spotify_lastfm") {
    body = (
      <div className="flex flex-col items-center gap-3 py-6 text-center">
        <Blip pose="cheer" size={96} decorative />
        <p className="font-display text-xl font-semibold">First play seen ✓</p>
        <p className="text-sm text-text-muted">Your friends can now see what you play on {name}.</p>
      </div>
    );
  } else {
    body = (
      <ol className="flex flex-col gap-5">
        {p?.action === "redirect" && p.url && (
          <li className="flex flex-col gap-2">
            <p className="font-medium">Approve Jingle in {name}</p>
            <p className="text-sm text-text-muted">{name} will ask you to confirm. You&rsquo;ll come straight back here.</p>
            <Button onClick={() => window.location.assign(p.url as string)}>Continue to {name}</Button>
          </li>
        )}
        {p?.action === "lastfm_then_spotify" && p.url && initialStep !== "link_spotify_lastfm" && (
          <li className="flex flex-col gap-2">
            <p className="font-medium">Approve Jingle on Last.fm</p>
            <p className="text-sm text-text-muted">
              Spotify shares what you play on every device through its built-in Last.fm link. Approve Jingle there first;
              you&rsquo;ll come straight back.
            </p>
            <Button onClick={() => window.location.assign(p.url as string)}>Continue</Button>
          </li>
        )}
        {(p?.action === "lastfm_then_spotify" || initialStep === "link_spotify_lastfm") && (
          <li className="flex flex-col gap-2">
            <p className="font-medium">Turn on Spotify&rsquo;s Last.fm link (one time)</p>
            <p className="text-sm text-text-muted">
              Open your Last.fm settings, choose Applications, and connect Spotify. Then play anything in Spotify on any
              device.
            </p>
            <a
              href="https://www.last.fm/settings/applications"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-sm font-medium text-accent-text underline-offset-4 hover:underline"
            >
              Open Last.fm settings <Icons.Open size={14} />
            </a>
          </li>
        )}
        <BrowserSteps platform={platform} returnTo={returnTo} slow={slow} />
        <li>
          <details className="rounded-md border border-border p-3 text-sm">
            <summary className="cursor-pointer font-medium">Other ways to connect</summary>
            <div className="mt-3 flex flex-col gap-4">
              {platform === "YOUTUBE_MUSIC" && <TakeoutUpload />}
              <p className="text-text-muted">Already use ListenBrainz or Last.fm? Connect it instead.</p>
              <ListenBrainzForm platform={platform} />
              <LastfmForm platform={platform} />
              <Link href="/settings/connections" className="text-accent-text underline-offset-4 hover:underline">
                Connection settings
              </Link>
            </div>
          </details>
        </li>
      </ol>
    );
  }

  return (
    <Sheet
      open
      onClose={onClose}
      title={`Connect ${name}`}
      description={p?.live_on_phone ? CAPABILITY[platform].promise : platform === "SPOTIFY" ? "You'll show as live when you play Spotify in this browser." : CAPABILITY[platform].promise}
      footer={
        <Button variant={done ? "primary" : "ghost"} onClick={onClose}>
          {done ? "Done" : "Skip for now"}
        </Button>
      }
    >
      {body}
    </Sheet>
  );
}
