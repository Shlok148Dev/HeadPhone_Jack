"use client";

import Link from "next/link";
import { Artwork, IconButton, Icons, Pulse, cn, type FeedCardData } from "@/components/ds";
import { isFreshLive, sortFeed, useFeed } from "@/lib/feed";
import { useRealtimeStatus } from "@/lib/realtime";
import { songFromCard, useOpenSend } from "@/lib/send";

/** Server state only (BR-01): Live is what the server says, and no older than 90 s. */
export function pulseOf(c: FeedCardData, now: number) {
  return isFreshLive(c, now) && !c.degraded ? "live" : c.state === "RECENT" ? "recent" : "none";
}

/** Sidebar "Live now" (1024–1439 px): who is playing right now, at a glance. */
export function SidebarLive() {
  const feed = useFeed(useRealtimeStatus() === "live");
  const now = Date.now();
  const live = (feed.data?.results ?? []).filter((c) => pulseOf(c, now) === "live").slice(0, 6);
  return (
    <section aria-labelledby="side-live-h" className="mt-6 hidden flex-col gap-1 lg:flex">
      <h2 id="side-live-h" className="flex items-center gap-2 px-3 font-mono text-[11px] uppercase tracking-wider text-text-muted">
        <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-live" />
        Live now
      </h2>
      {live.length === 0 ? (
        <p className="px-3 text-xs text-text-muted">Nobody&rsquo;s playing right now.</p>
      ) : (
        <ul className="flex flex-col">
          {live.map((c) => (
            <li key={c.friend.id}>
              <Link
                href={`/u/${c.friend.username}`}
                className="flex min-h-11 items-center gap-2.5 rounded-md px-2 py-1.5 hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)]"
              >
                <Pulse state="live" name={c.friend.display_name} url={c.friend.avatar_url} seed={c.friend.id} size={26} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13px] font-medium">{c.friend.display_name}</span>
                  <span className="block truncate text-xs text-text-muted">{c.recording?.title}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/**
 * Friend activity (≥ 1440 px), Jingle's answer to Spotify's friend feed: the Pulse, the track with
 * its real cover, an honest time, and one tap to send something back.
 */
/** Friend activity, opened from the top bar (D-SHELL-04): overlays at lg, docks at xl. */
export function ActivityPanel({ onClose }: { onClose: () => void }) {
  const feed = useFeed(useRealtimeStatus() === "live");
  const openSend = useOpenSend();
  const now = Date.now();
  const cards = sortFeed(feed.data?.results ?? []).filter((c) => c.recording && c.state !== "HIDDEN");
  return (
    <aside
      aria-label="Friend activity"
      className="jg-enter fixed bottom-0 right-0 top-0 z-40 hidden w-[320px] flex-col border-l border-border bg-surface-1 shadow-2 lg:flex xl:z-20 xl:shadow-none"
    >
      <div className="flex h-16 items-center justify-between pl-5 pr-2">
        <h2 className="font-display text-lg font-semibold">Friend activity</h2>
        <IconButton label="Close friend activity" onClick={onClose}>
          <Icons.Close size={18} />
        </IconButton>
      </div>
      <ul className="ds-scrollbar-none flex flex-1 flex-col gap-1 overflow-y-auto px-3 pb-28" aria-live="polite" aria-relevant="additions">
        {cards.map((c) => {
          const state = pulseOf(c, now);
          const rec = c.recording!;
          return (
            // Grid: the state label spans under the art and action, so "Live on YouTube Music" stays on one line.
            <li key={c.friend.id} className="group grid grid-cols-[auto_minmax(0,1fr)_auto_auto] items-start gap-x-3 rounded-md px-2 py-2.5 hover:bg-surface-2">
              <Link href={`/u/${c.friend.username}`} className="row-span-2 shrink-0 rounded-pill focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)]" aria-label={c.friend.display_name}>
                <Pulse state={state} name={c.friend.display_name} url={c.friend.avatar_url} seed={c.friend.id} size={34} />
              </Link>
              <div className="min-w-0">
                <p className="truncate text-[13px] font-semibold">{c.friend.display_name}</p>
                <p className="truncate text-[13px]" title={`${rec.title} · ${rec.artist}`}>
                  {rec.title}
                </p>
                <p className="truncate text-xs text-text-muted">{rec.artist}</p>
              </div>
              <div className="h-10 w-10 shrink-0 overflow-hidden rounded-[var(--r-art-sm)]">
                <Artwork url={rec.artwork_small ?? rec.artwork_url} seed={rec.id ?? `${c.friend.id}|${rec.title}`} alt="" rounded="none" />
              </div>
              <IconButton
                label={`Send ${c.friend.display_name} something back`}
                variant="ghost"
                className="-mr-1 -mt-0.5 opacity-70 group-hover:opacity-100 focus-visible:opacity-100"
                onClick={() => openSend({ song: songFromCard(c) })}
              >
                <Icons.Send size={16} />
              </IconButton>
              <p className={cn("col-span-3 mt-0.5 truncate font-mono text-[11px]", state === "live" ? "text-live-text" : "text-text-muted")}>{c.freshness_label}</p>
            </li>
          );
        })}
        {!cards.length && !feed.isLoading && <li className="px-2 text-sm text-text-muted">When friends play music, it shows up here.</li>}
      </ul>
    </aside>
  );
}
