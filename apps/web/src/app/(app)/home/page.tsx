"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
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
import { SuggestionsShelf } from "@/components/app/Suggestions";
import { useAuth } from "@/lib/auth";
import { isFreshLive, useFeed } from "@/lib/feed";
import { useConnections, useMyCard } from "@/lib/queries";
import { useRealtimeStatus } from "@/lib/realtime";

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
 * JNG-05-01…08. Circle chips join in Sprint 6; the hero carousel arrives with Blends and recaps.
 */
export default function HomePage() {
  const { me } = useAuth();
  const router = useRouter();
  const realtime = useRealtimeStatus();
  const feed = useFeed(realtime === "live");
  const mine = useMyCard();
  const connections = useConnections();
  const now = useTick();
  const [filter, setFilter] = useState("all");

  const myPlatform: Platform | undefined = useMemo(() => {
    if (mine.data?.platform && mine.data.platform !== "UNKNOWN") return mine.data.platform;
    return connections.data?.find((c) => c.status === "CONNECTED")?.platform;
  }, [mine.data, connections.data]);

  const cards = feed.data?.results ?? [];
  const live = cards.filter((c) => isFreshLive(c, now));
  const liveIds = new Set(live.map((c) => c.friend.id));
  // "All": Live friends sit in the shelf above, so the grid is everyone else (UX_SPEC §5.4).
  const shown = filter === "live" ? live : cards.filter((c) => !liveIds.has(c.friend.id));
  const hasFriends = cards.length > 0;

  return (
    <div className="flex flex-col gap-8">
      <h1 className="font-display text-3xl font-semibold tracking-tight md:text-4xl">
        {greeting()}, {me?.display_name || me?.username}
      </h1>

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
              ]}
            />
            {feed.data?.degraded && (
              <p className="font-mono text-xs text-text-muted">Some friends&rsquo; plays may be delayed. Showing the latest we have.</p>
            )}
          </div>

          {filter === "all" &&
            (live.length ? (
              <Shelf title="Live now" live count={live.length} itemWidth="clamp(148px, 40vw, 200px)">
                {live.map((c, i) => (
                  <FeedCard key={c.friend.id} card={c} myPlatform={myPlatform} index={i} sharedLayout={false} />
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
              {filter === "live" ? "Live now" : live.length ? "Everyone else" : "Your friends"}
            </h2>
            {shown.length ? (
              <ul className="grid grid-cols-[repeat(auto-fill,minmax(148px,1fr))] gap-4 md:grid-cols-[repeat(auto-fill,minmax(184px,1fr))] xl:grid-cols-[repeat(auto-fill,minmax(200px,1fr))]">
                {shown.map((c, i) => (
                  <li key={c.friend.id}>
                    <FeedCard card={c} myPlatform={myPlatform} index={i} sharedLayout={false} />
                  </li>
                ))}
              </ul>
            ) : (
              <div className="flex flex-col items-start gap-2">
                <p className="text-sm text-text-muted">No one&rsquo;s live right now.</p>
                <Button variant="ghost" onClick={() => setFilter("all")}>Show everyone</Button>
              </div>
            )}
          </section>
        </>
      )}

      <SuggestionsShelf />

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
            <FeedCard card={mine.data} myPlatform={myPlatform} sharedLayout={false} />
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
