"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Blip, Button, ButtonLink, Icons, PlatformBadge, Sheet, cn, type Platform } from "@/components/ds";
import { useConnections, type Connection } from "@/lib/queries";

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

/**
 * Honest capability lines (UX_SPEC §10, web-phase pilot). Spotify's any-device Live arrives with
 * its Last.fm link in Sprint 2; until then every platform is Live in the browser only.
 */
const CAPABILITY: Record<MusicPlatform, { line: string; promise: string }> = {
  SPOTIFY: {
    line: "Live in your browser",
    promise: "You'll show as live when you play Spotify in this browser.",
  },
  APPLE_MUSIC: {
    line: "Live in your browser",
    promise:
      "You'll show as live when you play in your browser. Phone listening on Apple Music isn't shared yet.",
  },
  YOUTUBE_MUSIC: {
    line: "Live in your browser · history by import",
    promise:
      "You'll show as live when you play in your browser. Phone listening on YouTube Music shows up after you import your history.",
  },
  AMAZON_MUSIC: {
    line: "Live in your browser",
    promise:
      "You'll show as live when you play in your browser. Phone listening on Amazon Music doesn't show yet.",
  },
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
        primary ? "border-transparent [background:linear-gradient(var(--surface-2),var(--surface-2))_padding-box,var(--gradient-brand)_border-box] border-2" : "border-border",
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <PlatformBadge platform={platform} />
        {status && <span className="font-mono text-xs text-text-muted">{status}</span>}
      </div>
      <p className="text-sm text-text-muted">{CAPABILITY[platform].line}</p>
      <Button variant={primary && !connected ? "primary" : "secondary"} onClick={() => onConnect(platform)}>
        {connected ? `Manage ${NAMES[platform]}` : `Connect ${NAMES[platform]}`}
      </Button>
    </div>
  );
}

/**
 * Connect sheet (BR-13): one flow per platform; the user never picks a route. In the pilot the
 * browser path is the Jingle Companion; the pairing itself happens on /connect/companion.
 */
export function ConnectSheet({
  platform,
  onClose,
  returnTo,
}: {
  platform: MusicPlatform | null;
  onClose: () => void;
  returnTo: string;
}) {
  const connections = useConnections({ poll: platform !== null });
  const conn = connections.data?.find((c) => c.platform === platform);
  const [waitingSince] = useState(() => Date.now());
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    if (!platform) return;
    const t = setTimeout(() => setSlow(true), 120_000);
    return () => clearTimeout(t);
  }, [platform, waitingSince]);

  if (!platform) return <Sheet open={false} onClose={onClose} title="" />;
  const name = NAMES[platform];
  const done = conn?.status === "CONNECTED" && conn.first_play_at;
  const pairHref = `/connect/companion?return=${encodeURIComponent(returnTo)}`;

  return (
    <Sheet
      open
      onClose={onClose}
      title={`Connect ${name}`}
      description={CAPABILITY[platform].promise}
      footer={
        <Button variant={done ? "primary" : "ghost"} onClick={onClose}>
          {done ? "Done" : "Skip for now"}
        </Button>
      }
    >
      {done ? (
        <div className="flex flex-col items-center gap-3 py-6 text-center">
          <Blip pose="cheer" size={96} decorative />
          <p className="font-display text-xl font-semibold">First play seen ✓</p>
          <p className="text-sm text-text-muted">Your friends can now see what you play on {name} in this browser.</p>
        </div>
      ) : (
        <ol className="flex flex-col gap-5">
          <li className="flex flex-col gap-2">
            <p className="font-medium">1. Install the Jingle Companion for your browser</p>
            <p className="text-sm text-text-muted">
              It notices what you play in {name}&rsquo;s web player and shares it only with your Jingle account. For
              the pilot, install it from the file your Jingle host gave you (Chrome or Edge: Extensions → Developer
              mode → Load unpacked).
            </p>
          </li>
          <li className="flex flex-col gap-2">
            <p className="font-medium">2. Connect this browser</p>
            <ButtonLink href={pairHref} variant="primary" leadingIcon={<Icons.Plug size={18} />}>
              Connect this browser
            </ButtonLink>
          </li>
          <li className="flex flex-col gap-2">
            <p className="font-medium">3. Play any song in {name} now</p>
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
                {slow
                  ? `No play yet. Make sure ${name} is playing in this browser, then try again.`
                  : "Listening for your first play…"}
              </p>
            </div>
          </li>
          <li>
            <details className="rounded-md border border-border p-3 text-sm">
              <summary className="cursor-pointer font-medium">Other ways to connect</summary>
              <p className="mt-2 text-text-muted">
                {platform === "SPOTIFY"
                  ? "Listening on your phone? Linking Spotify with Last.fm so friends see you live on any device arrives in the next update."
                  : platform === "YOUTUBE_MUSIC"
                    ? "Importing your YouTube history (Google Takeout file) arrives in the next update."
                    : "Already use ListenBrainz or Last.fm? Connecting them arrives in the next update."}{" "}
                <Link href="/settings/connections" className="text-accent-text underline-offset-4 hover:underline">
                  Connection settings
                </Link>
              </p>
            </details>
          </li>
        </ol>
      )}
    </Sheet>
  );
}
