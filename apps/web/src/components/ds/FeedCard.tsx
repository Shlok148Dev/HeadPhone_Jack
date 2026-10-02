"use client";

import * as motion from "motion/react-m";
import { useId, type CSSProperties } from "react";
import { useMotionSafe } from "@/lib/motion";
import { Avatar } from "./Avatar";
import { DelayedTag, LiveBadge } from "./Badges";
import { buttonClasses, IconButton } from "./Button";
import { Artwork } from "./GenerativeCover";
import { Lock, Open, Send } from "./icons";
import { Pulse } from "./Pulse";
import { PLATFORM_NAMES, type FeedCardData, type FeedRecording, type Platform } from "./types";
import { cn } from "./utils";

export interface FeedCardProps {
  card: FeedCardData;
  /** The viewer's own platform, used to pick the "Open in my app" link. */
  myPlatform?: Platform;
  onSend?: (card: FeedCardData) => void;
  /** TOP cards: the friend's top artworks (up to 4) for the 2×2 stack. */
  topRecordings?: FeedRecording[];
  /** Shared-element `layoutId="card-{friend.id}"` for card→detail. Turn off when the same friend renders twice on a page. */
  sharedLayout?: boolean;
  /** Position in a list, for staggered entry. */
  index?: number;
  className?: string;
}

/**
 * JNG-06-03: open on the viewer's own platform. Verified link on my platform → search on my
 * platform ("Search in Apple Music") → the friend's platform → any verified link.
 */
function pickLink(
  rec: FeedRecording,
  mine: Platform | undefined,
  source: Platform,
): { url: string; searchOn: Platform | null } | null {
  const links = rec.links ?? {};
  const search = rec.search_links ?? {};
  if (mine && links[mine]) return { url: links[mine] as string, searchOn: null };
  if (mine && mine !== "UNKNOWN" && search[mine]) return { url: search[mine] as string, searchOn: mine };
  if (links[source]) return { url: links[source] as string, searchOn: null };
  for (const v of Object.values(links)) if (v) return { url: v, searchOn: null };
  if (source !== "UNKNOWN" && search[source]) return { url: search[source] as string, searchOn: source };
  return null;
}

function seedFor(rec: FeedRecording, friendId: string) {
  return rec.id ?? `${friendId}|${rec.title}`;
}

/**
 * A friend's listening card (CONTRACTS.md §7, UX_SPEC §4.6).
 * - `freshness_label` is rendered verbatim (the server builds it; the client never does).
 * - Live styling appears ONLY when `state === "LIVE"` (and never while degraded).
 */
export function FeedCard({ card, myPlatform, onSend, topRecordings, index = 0, sharedLayout = true, className }: FeedCardProps) {
  const m = useMotionSafe();
  const uid = useId();
  const titleId = `${uid}-t`;
  const labelId = `${uid}-l`;
  const isLive = card.state === "LIVE" && !card.degraded;
  const name = card.friend.display_name || card.friend.username;
  const rec = card.state === "HIDDEN" ? null : card.recording;

  const label = (
    <p id={labelId} className="flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-1">
      <span className={cn("font-mono text-xs font-medium", isLive ? "text-live-text" : "text-text-muted")} data-testid="freshness-label">
        {card.freshness_label}
      </span>
      {card.degraded && (
        <>
          <span aria-hidden="true" className="font-mono text-xs text-text-muted">
            ·
          </span>
          <DelayedTag />
        </>
      )}
    </p>
  );

  const shell = cn(
    "group flex flex-col gap-2 rounded-lg p-2 motion-safe:transition-colors motion-safe:duration-200 hover:bg-surface-1 focus-within:bg-surface-1",
    className,
  );

  if (!rec) {
    return (
      <motion.article {...m.enter(index)} aria-label={`${name}. Activity hidden.`} data-state={card.state} className={shell}>
        <div className="relative flex aspect-square w-full items-center justify-center rounded-md bg-surface-2">
          <Avatar name={name} url={card.friend.avatar_url} seed={card.friend.id} size={72} decorative />
          <span aria-hidden="true" className="absolute bottom-3 right-3 text-text-muted">
            <Lock size={16} />
          </span>
        </div>
        <p id={titleId} className="truncate text-[15px] font-semibold text-text">
          {name}
        </p>
        {label}
      </motion.article>
    );
  }

  const isTop = card.state === "TOP";
  const unresolved = rec.id === null;
  const spotifyData = card.attribution === "SPOTIFY";
  const picked = pickLink(rec, myPlatform, card.platform);
  const link = spotifyData ? (rec.links?.SPOTIFY ?? picked?.url ?? null) : (picked?.url ?? null);
  const platformName = card.platform === "UNKNOWN" ? null : PLATFORM_NAMES[card.platform];
  const searchOn = !spotifyData && picked?.searchOn && picked.searchOn !== "UNKNOWN" ? PLATFORM_NAMES[picked.searchOn] : null;
  const openLabel = spotifyData
    ? "Open Spotify"
    : searchOn
      ? `Search in ${searchOn}`
      : unresolved && platformName
        ? `Search in ${platformName}`
        : "Open in my app";
  const tops = isTop ? [rec, ...(topRecordings ?? [])].slice(0, 4) : [];

  // Destination app shown as text next to the icon: "Apple Music", "Spotify"…; the full
  // sentence ("Search in Apple Music") is the link's accessible name.
  const dest = spotifyData ? "Spotify" : (searchOn ?? (myPlatform && myPlatform !== "UNKNOWN" ? PLATFORM_NAMES[myPlatform] : platformName ?? "my app"));
  const artColor = rec.artwork_colors?.accent;

  return (
    <motion.article
      {...m.enter(index)}
      aria-labelledby={titleId}
      aria-describedby={labelId}
      data-state={card.state}
      className={shell}
    >
      <span className="ds-visually-hidden" id={titleId}>
        {`${name}: ${rec.title} by ${rec.artist}. ${card.freshness_label}${card.degraded ? ", delayed" : ""}`}
      </span>

      {/* Artwork stays untouched (no text, badges or controls on it): Live shows on the person. */}
      <motion.div layoutId={sharedLayout ? `card-${card.friend.id}` : undefined} className="relative">
        {isTop && tops.length > 1 ? (
          <div className="grid aspect-square w-full grid-cols-2 gap-0.5 overflow-hidden rounded-[8px]">
            {Array.from({ length: 4 }, (_, i) => tops[i] ?? tops[0]!).map((r, i) => (
              <Artwork key={i} url={r.artwork_small ?? r.artwork_url} seed={seedFor(r, card.friend.id) + (tops[i] ? "" : `#${i}`)} alt="" rounded="none" />
            ))}
          </div>
        ) : (
          <div
            className={cn(
              "jg-art-glow rounded-[8px] motion-safe:transition-transform motion-safe:duration-200 group-hover:-translate-y-0.5",
              isLive && "ring-2 ring-live ring-offset-2 ring-offset-bg",
            )}
            style={artColor ? ({ "--art": artColor } as CSSProperties) : undefined}
          >
            <div className="overflow-hidden rounded-[8px]">
              <Artwork url={rec.artwork_url} seed={seedFor(rec, card.friend.id)} alt="" rounded="none" tint={rec.artwork_colors?.dominant} />
            </div>
          </div>
        )}
      </motion.div>

      <div className="flex min-w-0 items-center gap-2 pt-1.5">
        <Pulse state={isLive ? "live" : card.state === "RECENT" ? "recent" : "none"} name={name} url={card.friend.avatar_url} seed={card.friend.id} size={20} />
        <span className="min-w-0 flex-1 truncate text-[13px] font-semibold text-text">{name}</span>
        {isLive && <LiveBadge seed={card.friend.id} />}
      </div>

      {isTop ? (
        <div className="flex min-w-0 flex-col items-start gap-1.5">
          <span id={labelId} className="inline-flex h-6 items-center gap-1.5 rounded-pill bg-surface-3 px-2.5 font-mono text-xs font-medium text-text-muted" data-testid="freshness-label">
            {card.freshness_label}
          </span>
          {card.degraded && <DelayedTag />}
          <p className="truncate text-[13px] text-text-muted">
            {rec.artist}
            {tops.length > 1 ? ` and ${tops.length - 1} more` : ""}
          </p>
        </div>
      ) : (
        <div className="flex min-w-0 flex-col gap-0.5">
          <p className="truncate text-[15px] font-semibold leading-tight text-text">{rec.title}</p>
          <p className="truncate text-[13px] text-text-muted">{rec.artist}</p>
          <div className="mt-1">{label}</div>
        </div>
      )}

      <div className="flex items-center gap-1">
        {link ? (
          <a
            href={link}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`${openLabel}: ${rec.title}`}
            title={openLabel}
            className={buttonClasses("secondary", "md", "min-w-0 flex-1 justify-start gap-1.5 px-3 text-[13px]")}
          >
            <Open size={15} />
            <span className="truncate">{dest}</span>
          </a>
        ) : (
          <span aria-disabled="true" aria-label={openLabel} className={buttonClasses("secondary", "md", "min-w-0 flex-1 justify-start gap-1.5 px-3 text-[13px]")}>
            <Open size={15} />
            <span className="truncate">{dest}</span>
          </span>
        )}
        <IconButton label={`Send ${rec.title}`} variant="ghost" onClick={() => onSend?.(card)}>
          <Send />
        </IconButton>
      </div>

      {spotifyData && (
        <a
          href={rec.links?.SPOTIFY ?? "https://open.spotify.com"}
          target="_blank"
          rel="noopener noreferrer"
          className="ds-focus -my-2 inline-flex min-h-11 w-fit items-center rounded-sm font-mono text-[11px] text-text-muted underline underline-offset-2 hover:text-text"
        >
          Data from Spotify
        </a>
      )}
    </motion.article>
  );
}
