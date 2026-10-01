"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import {
  Blip,
  Button,
  EmptyState,
  ErrorState,
  FeedCard,
  FeedCardSkeleton,
  FilterChips,
  Shelf,
  Skeleton,
  type Platform,
} from "@/components/ds";
import { useAuth } from "@/lib/auth";
import { songFromCard, useOpenSend } from "@/lib/send";
import { useCircles } from "@/lib/circles";
import { isFreshLive, useFeed } from "@/lib/feed";
import { useConnections, useMyCard } from "@/lib/queries";
import { useRealtimeStatus } from "@/lib/realtime";

// Below the fold: loads after first paint so Home stays inside its JS budget (R-D).
const HomeHero = lazy(() => import("@/components/app/HomeExtras").then((m) => ({ default: m.HomeHero })));
const HomeShelves = lazy(() => import("@/components/app/HomeExtras").then((m) => ({ default: m.HomeShelves })));
const SuggestionsShelf = lazy(() => import("@/components/app/Suggestions").then((m) => ({ default: m.SuggestionsShelf })));

/** "Aanya Rao" → "Aanya"; a placeholder name like "You (demo)" gets no name at all. */
function firstName(name?: string | null): string {
  const first = (name ?? "").replace(/\(.*?\)/g, "").trim().split(/\s+/)[0] ?? "";
  return /^you$/i.test(first) ? "" : first;
}

function greeting(now = new Date()): string {
  const h = now.getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

/** Re-render every 15 s so Live cards past 90 s drop out of the shelf between updates. */
function useTick(ms = 15_000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), ms);
    return () => clearInterval(t);
  }, [ms]);
  return now;
}

/**
 * Home (UX_SPEC §5.4): Live now shelf, filter chips, every friend's card, and me.
 * JNG-05-01…08; circle chips narrow the feed to one circle (JNG-05-03). The hero carousel arrives
 * with Blends and recaps.
 */
export default function HomePage() {
  const { me } = useAuth();
  const openSend = useOpenSend();
  const router = useRouter();
  const realtime = useRealtimeStatus();
  const [filter, setFilter] = useState("all");
  const circleId = filter.startsWith("c:") ? filter.slice(2) : undefined;
  const allFeed = useFeed(realtime === "live");
  const circleFeed = useFeed(realtime === "live", circleId);
  const feed = circleId ? circleFeed : allFeed;
  const circles = useCircles();
  const mine = useMyCard();
  const connections = useConnections();
  const now = useTick();

  const myPlatform: Platform | undefined = useMemo(() => {
    if (mine.data?.platform && mine.data.platform !== "UNKNOWN") return mine.data.platform;
    return connections.data?.find((c) => c.status === "CONNECTED")?.platform;
  }, [mine.data, connections.data]);

  // Spotify Web API content lives in its own attributed module, never mixed (docs/ux D-BR-01).
  const allCards = feed.data?.results ?? [];
  const spotifyCards = allCards.filter((c) => c.attribution === "SPOTIFY");
  const cards = allCards.filter((c) => c.attribution !== "SPOTIFY");
  const live = cards.filter((c) => isFreshLive(c, now));
  const liveIds = new Set(live.map((c) => c.friend.id));
  // "All": Live friends sit in the shelf above, so the grid is everyone else (UX_SPEC §5.4).
  const shown = filter === "live" ? live : cards.filter((c) => !liveIds.has(c.friend.id));
  const hasFriends = allCards.length > 0 || !!circleId;

  return (
    <div className="flex flex-col gap-8">
      <h1 className="font-display text-3xl font-semibold tracking-tight md:text-4xl">
        {greeting()}
        {firstName(me?.display_name || me?.username) ? `, ${firstName(me?.display_name || me?.username)}` : ""}
      </h1>
      <Suspense fallback={<div className="min-h-[220px] rounded-[20px] bg-surface-1" aria-hidden />}>
        <HomeHero />
      </Suspense>

      {feed.isLoading ? (
        <div className="flex flex-col gap-4" aria-busy="true">
          <Skeleton className="h-9 w-40" rounded="pill" />
          <div className="flex gap-4 overflow-hidden">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="w-[148px] shrink-0 md:w-[184px]">
                <FeedCardSkeleton />
              </div>
            ))}
          </div>
        </div>
      ) : feed.isError ? (
        <ErrorState title="We couldn't load your feed." message="This is on us. Try again in a moment." onRetry={() => void feed.refetch()} retrying={feed.isFetching} />
      ) : !hasFriends ? (
        <section className="rounded-lg border border-border bg-surface-1">
          <EmptyState
            pose="wave"
            title="Your feed is waiting for friends"
            description="Add a friend and you'll see what they're playing here."
            action={{ label: "Invite friends", onClick: () => router.push("/friends?tab=find") }}
          />
        </section>
      ) : (
        <>
          <div className="flex flex-col gap-2">
            <FilterChips
              label="Filter your feed"
              value={filter}
              onChange={setFilter}
              options={[
                { value: "all", label: "All" },
                { value: "live", label: live.length ? `Live · ${live.length}` : "Live" },
                ...(circles.data ?? []).map((c) => ({ value: `c:${c.id}`, label: c.name })),
              ]}
            />
            {feed.data?.degraded && (
              <p className="font-mono text-xs text-text-muted">Some friends&rsquo; plays may be delayed. Showing the latest we have.</p>
            )}
          </div>

          {filter !== "live" &&
            (live.length ? (
              <Shelf title="Live now" live count={live.length} itemWidth="clamp(148px, 40vw, 200px)">
                {live.map((c, i) => (
                  <FeedCard key={c.friend.id} card={c} myPlatform={myPlatform} index={i} sharedLayout={false} onSend={(x) => openSend({ song: songFromCard(x) })} />
                ))}
              </Shelf>
            ) : (
              <section aria-labelledby="live-h" className="flex items-center gap-3 rounded-lg border border-border bg-surface-1 p-4">
                <h2 id="live-h" className="sr-only">Live now</h2>
                <Blip pose="sleepy" size={48} decorative />
                <p className="text-sm text-text-muted">No one&rsquo;s playing right now.</p>
              </section>
            ))}

          <section aria-labelledby="friends-h" className="flex flex-col gap-3">
            <h2 id="friends-h" className="font-display text-xl font-semibold">
              {filter === "live" ? "Live now" : live.length ? "Everyone else" : circleId ? "In this circle" : "Your friends"}
            </h2>
            {shown.length ? (
              <ul className="grid grid-cols-[repeat(auto-fill,minmax(148px,1fr))] gap-4 md:grid-cols-[repeat(auto-fill,minmax(184px,1fr))] xl:grid-cols-[repeat(auto-fill,minmax(200px,1fr))]">
                {shown.map((c, i) => (
                  <li key={c.friend.id}>
                    <FeedCard card={c} myPlatform={myPlatform} index={i} sharedLayout={false} onSend={(x) => openSend({ song: songFromCard(x) })} />
                  </li>
                ))}
              </ul>
            ) : (
              <div className="flex flex-col items-start gap-2">
                <p className="text-sm text-text-muted">{circleId ? "Everyone in this circle is live above." : "No one’s live right now."}</p>
                <Button variant="ghost" onClick={() => setFilter("all")}>Show everyone</Button>
              </div>
            )}
          </section>
        </>
      )}

      {spotifyCards.length > 0 && (
        <section aria-labelledby="spotify-h" className="flex flex-col gap-3 rounded-[12px] border border-border p-3">
          <h2 id="spotify-h" className="font-display text-xl font-semibold">From Spotify</h2>
          <ul className="grid grid-cols-[repeat(auto-fill,minmax(148px,1fr))] gap-4 md:grid-cols-[repeat(auto-fill,minmax(184px,1fr))]">
            {spotifyCards.map((c, i) => (
              <li key={c.friend.id}>
                <FeedCard card={c} myPlatform={myPlatform} index={i} sharedLayout={false} />
              </li>
            ))}
          </ul>
        </section>
      )}

      <Suspense fallback={null}>
        <HomeShelves />
      </Suspense>

      <Suspense fallback={null}>
        <SuggestionsShelf />
      </Suspense>

      <section aria-labelledby="you-heading" className="flex flex-col gap-3">
        <div className="flex items-baseline justify-between">
          <h2 id="you-heading" className="font-display text-xl font-semibold">You right now</h2>
          <Link href="/settings/connections" className="text-sm text-text-muted underline-offset-4 hover:text-text hover:underline">
            Your music apps
          </Link>
        </div>
        <div className="w-full max-w-[240px] sm:max-w-[280px]">
          {mine.isLoading ? (
            <FeedCardSkeleton />
          ) : mine.data && mine.data.recording && mine.data.state !== "HIDDEN" ? (
            <FeedCard card={mine.data} myPlatform={myPlatform} sharedLayout={false} onSend={(x) => openSend({ song: songFromCard(x) })} />
          ) : (
            <EmptyState
              pose="idle"
              title={connections.data?.some((c) => c.status === "CONNECTED") ? "Play something on any app" : "Connect your music"}
              action={connections.data?.some((c) => c.status === "CONNECTED") ? undefined : { label: "Connect your music", onClick: () => router.push("/onboarding/sources") }}
            />
          )}
        </div>
      </section>
    </div>
  );
}
