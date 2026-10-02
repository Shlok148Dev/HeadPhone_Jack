"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Artwork, Icons, PlatformMark, Pulse, buttonClasses, cn, type FeedCardData, type Platform } from "@/components/ds";
import { ambientStyle } from "@/lib/ambient";
import { isFreshLive } from "@/lib/feed";
import { useMotionSafe } from "@/lib/motion";
import { useTheme } from "@/lib/theme";
import { tuneIn } from "@/lib/tunein";

const ROTATE_MS = 9000;

/**
 * The Now stage (D-HOME-01): Home opens on one song a friend is playing, big and in its own
 * colour, with Tune in as the one primary action. Live friends first (server state only, BR-01),
 * else the freshest recent plays. Rotates calmly; pauses on hover/focus; still under reduced motion.
 */
export function NowStage({
  cards,
  now,
  myPlatform,
  onSend,
}: {
  cards: FeedCardData[];
  now: number;
  myPlatform?: Platform;
  onSend: (card: FeedCardData) => void;
}) {
  const { theme } = useTheme();
  const m = useMotionSafe();
  const stage = useMemo(() => {
    const playable = cards.filter((c) => c.recording && c.state !== "HIDDEN" && c.state !== "TOP");
    const live = playable.filter((c) => isFreshLive(c, now) && !c.degraded);
    return (live.length ? live : playable.filter((c) => c.state === "RECENT")).slice(0, 6);
    // Re-pick only when who is on stage changes, not on every clock tick.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cards.map((c) => `${c.friend.id}:${c.state}:${c.recording?.title}`).join("|")]);
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (stage.length < 2 || paused || m.reduced) return;
    const t = window.setInterval(() => setIndex((i) => (i + 1) % stage.length), ROTATE_MS);
    return () => window.clearInterval(t);
  }, [stage.length, paused, m.reduced]);

  if (!stage.length)
    return (
      <section aria-labelledby="now-stage-h" className="flex items-center gap-3 rounded-[28px] border border-border bg-surface-1 p-5">
        <h2 id="now-stage-h" className="sr-only">Playing now</h2>
        <p className="text-sm text-text-muted">Nobody&rsquo;s playing right now. When a friend presses play, it shows up here.</p>
      </section>
    );
  const card = stage[index % stage.length]!;
  const rec = card.recording!;
  const live = isFreshLive(card, now) && !card.degraded;
  const name = card.friend.display_name || card.friend.username;
  const tune = tuneIn(rec, myPlatform, card.platform);

  return (
    <section
      aria-labelledby="now-stage-h"
      className="relative overflow-hidden rounded-[28px] border border-border/60 motion-safe:transition-[background] motion-safe:duration-700"
      style={ambientStyle(rec.artwork_colors, theme)}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <h2 id="now-stage-h" className="sr-only">
        {live ? "Playing now" : "Just played"}
      </h2>
      <div className="grid items-center gap-6 p-5 sm:p-8 md:grid-cols-[auto_minmax(0,1fr)] md:gap-10 lg:p-10">
        <div
          key={`${card.friend.id}|${rec.title}`}
          className="jg-enter jg-art-glow mx-auto w-[min(70vw,300px)] overflow-hidden rounded-[var(--r-art-lg)] md:mx-0 md:w-[clamp(220px,22vw,320px)]"
          style={{ ["--art" as string]: rec.artwork_colors?.accent ?? "transparent" }}
        >
          <Artwork
            url={rec.artwork_url}
            seed={rec.id ?? `${card.friend.id}|${rec.title}`}
            alt={`${rec.title} by ${rec.artist}`}
            rounded="none"
            eager
            tint={rec.artwork_colors?.dominant}
            sizes="(min-width: 768px) 320px, 70vw"
          />
        </div>

        <div className="min-w-0">
          <p className="flex items-center gap-2 font-mono text-xs uppercase tracking-[0.14em] text-text-muted">
            {live ? (
              <span className="inline-flex items-center gap-1.5 text-live-text">
                <span aria-hidden className="jg-pulse-ring h-2 w-2 rounded-full bg-[var(--live)]" />
                Live now
              </span>
            ) : (
              <span>Just played</span>
            )}
          </p>
          <p className="mt-3 line-clamp-2 font-display text-4xl font-semibold leading-[0.98] tracking-tight [text-wrap:balance] md:text-5xl xl:text-6xl">
            {rec.title}
          </p>
          <p className="mt-2 truncate text-lg text-text-muted">{rec.artist}</p>

          <div className="mt-5 flex min-w-0 items-center gap-3">
            <Link href={`/u/${card.friend.username}`} className="shrink-0 rounded-full focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)]" aria-label={`${name}'s profile`}>
              <Pulse state={live ? "live" : "recent"} name={name} url={card.friend.avatar_url} seed={card.friend.id} size={34} />
            </Link>
            <p className="min-w-0 text-sm">
              <span className="font-semibold">{name}</span> <span className="text-text-muted">{live ? "is listening" : "played this"}</span>
              <span className={cn("block truncate font-mono text-xs", live ? "text-live-text" : "text-text-muted")}>{card.freshness_label}</span>
            </p>
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            {tune && (
              <a href={tune.url} target="_blank" rel="noopener noreferrer" className={buttonClasses("primary", "lg", "gap-2.5 px-7")} aria-label={`${tune.label}: ${rec.title}`}>
                {tune.platform !== "UNKNOWN" ? <PlatformMark platform={tune.platform} size={18} mono /> : <Icons.Open size={18} />}
                {tune.label}
              </a>
            )}
            <button type="button" className={buttonClasses("secondary", "lg", "gap-2")} onClick={() => onSend(card)}>
              <Icons.Send size={17} />
              Send to a friend
            </button>
          </div>
        </div>
      </div>

      {stage.length > 1 && (
        <div className="flex items-center gap-2 px-5 pb-5 sm:px-8 lg:px-10" role="group" aria-label="Who else is playing">
          {stage.map((c, i) => {
            const n = c.friend.display_name || c.friend.username;
            const on = i === index % stage.length;
            return (
              <button
                key={c.friend.id}
                type="button"
                aria-pressed={on}
                aria-label={`Show ${n}`}
                onClick={() => setIndex(i)}
                className={cn("rounded-full transition-opacity focus-visible:outline-2 focus-visible:outline-[var(--focus-ring)]", on ? "opacity-100" : "opacity-60 hover:opacity-100")}
              >
                <Pulse state={isFreshLive(c, now) && !c.degraded ? "live" : "recent"} name={n} url={c.friend.avatar_url} seed={c.friend.id} size={on ? 30 : 26} />
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
