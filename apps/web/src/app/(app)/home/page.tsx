"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import {
  EmptyState,
  ErrorState,
  FeedCard,
  FeedCardSkeleton,
  Skeleton,
  type Platform,
} from "@/components/ds";
import { NowStage } from "@/components/app/NowStage";
import { useAuth } from "@/lib/auth";
import { songFromCard, useOpenSend } from "@/lib/send";
import { useFeed } from "@/lib/feed";
import { useConnections, useMyCard } from "@/lib/queries";
import { useRealtimeStatus } from "@/lib/realtime";

// Below the fold: loads after first paint so Home stays inside its JS budget (R-D).
const PendingReveal = lazy(() =>
  import("@/components/app/WeeklyCharts").then((m) => ({
    default: m.PendingReveal,
  })),
);
const WeeklyCharts = lazy(() =>
  import("@/components/app/WeeklyCharts").then((m) => ({
    default: m.WeeklyCharts,
  })),
);
const DailyDrop = lazy(() =>
  import("@/components/app/DailyDrop").then((m) => ({ default: m.DailyDrop })),
);
const HomeHero = lazy(() =>
  import("@/components/app/HomeExtras").then((m) => ({ default: m.HomeHero })),
);
const HomeShelves = lazy(() =>
  import("@/components/app/HomeExtras").then((m) => ({
    default: m.HomeShelves,
  })),
);
const SuggestionsShelf = lazy(() =>
  import("@/components/app/Suggestions").then((m) => ({
    default: m.SuggestionsShelf,
  })),
);

/** "Aanya Rao" → "Aanya"; a placeholder name like "You (demo)" gets no name at all. */
function firstName(name?: string | null): string {
  const first =
    (name ?? "")
      .replace(/\(.*?\)/g, "")
      .trim()
      .split(/\s+/)[0] ?? "";
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
  // D-HOME-02: Home shows friends' listening once, in the Now stage (no duplicate shelves).
  const feed = useFeed(realtime === "live");
  const mine = useMyCard();
  const connections = useConnections();
  const now = useTick();

  const myPlatform: Platform | undefined = useMemo(() => {
    if (mine.data?.platform && mine.data.platform !== "UNKNOWN")
      return mine.data.platform;
    return connections.data?.find((c) => c.status === "CONNECTED")?.platform;
  }, [mine.data, connections.data]);

  // Spotify Web API content lives in its own attributed module, never mixed (docs/ux D-BR-01).
  const allCards = feed.data?.results ?? [];
  const spotifyCards = allCards.filter((c) => c.attribution === "SPOTIFY");
  const cards = allCards.filter((c) => c.attribution !== "SPOTIFY");
  const hasFriends = allCards.length > 0;

  return (
    <div className="flex min-w-0 flex-col gap-8">
      <h1 className="font-display text-3xl font-semibold tracking-tight md:text-4xl">
        {greeting()}
        {firstName(me?.display_name || me?.username)
          ? `, ${firstName(me?.display_name || me?.username)}`
          : ""}
      </h1>
      {/* D-HOME-01: the stage (what a friend is playing, Tune in), then today's Drop, then rituals. */}
      {/* D-CHART-06: last week's chart reveal goes first while it's waiting. */}
      <Suspense fallback={null}>
        <PendingReveal />
      </Suspense>
      {feed.isLoading ? (
        <Skeleton className="h-[340px]" rounded="lg" />
      ) : feed.isError ? (
        <ErrorState
          title="We couldn't load your friends' music."
          message="This is on us. Try again in a moment."
          onRetry={() => void feed.refetch()}
          retrying={feed.isFetching}
        />
      ) : !hasFriends ? (
        <GetStarted
          connected={
            !!connections.data?.some(
              (c) =>
                c.status === "CONNECTED" || c.status === "PENDING_FIRST_PLAY",
            )
          }
        />
      ) : (
        <NowStage
          cards={cards}
          now={now}
          myPlatform={myPlatform}
          onSend={(c) => openSend({ song: songFromCard(c) })}
        />
      )}
      <Suspense
        fallback={
          <div
            className="min-h-[280px] rounded-[24px] bg-surface-1"
            aria-hidden
          />
        }
      >
        <DailyDrop myPlatform={myPlatform} />
      </Suspense>
      {/* D-CHART-01: Song and Artist of the Week among your people (replaces the old feed shelves). */}
      <Suspense
        fallback={
          <div
            className="min-h-[420px] rounded-[28px] bg-surface-1"
            aria-hidden
          />
        }
      >
        <WeeklyCharts myPlatform={myPlatform} quiet={!hasFriends} />
      </Suspense>
      <Suspense
        fallback={
          <div
            className="min-h-[220px] rounded-[20px] bg-surface-1"
            aria-hidden
          />
        }
      >
        <HomeHero />
      </Suspense>

      {spotifyCards.length > 0 && (
        <section
          aria-labelledby="spotify-h"
          className="flex flex-col gap-3 rounded-[12px] border border-border p-3"
        >
          <h2 id="spotify-h" className="font-display text-xl font-semibold">
            From Spotify
          </h2>
          <ul className="grid grid-cols-[repeat(auto-fill,minmax(148px,1fr))] gap-4 md:grid-cols-[repeat(auto-fill,minmax(184px,1fr))]">
            {spotifyCards.map((c, i) => (
              <li key={c.friend.id}>
                <FeedCard
                  card={c}
                  myPlatform={myPlatform}
                  index={i}
                  sharedLayout={false}
                />
              </li>
            ))}
          </ul>
        </section>
      )}

      <Suspense fallback={null}>
        <HomeShelves myPlatform={myPlatform} />
      </Suspense>

      <Suspense fallback={null}>
        <SuggestionsShelf />
      </Suspense>

      <section aria-labelledby="you-heading" className="flex flex-col gap-3">
        <div className="flex items-baseline justify-between">
          <h2 id="you-heading" className="font-display text-xl font-semibold">
            You right now
          </h2>
          <Link
            href="/settings/connections"
            className="text-sm text-text-muted underline-offset-4 hover:text-text hover:underline"
          >
            Your music apps
          </Link>
        </div>
        <div className="w-full max-w-[240px] sm:max-w-[280px]">
          {mine.isLoading ? (
            <FeedCardSkeleton />
          ) : mine.data &&
            mine.data.recording &&
            mine.data.state !== "HIDDEN" ? (
            <FeedCard
              card={mine.data}
              myPlatform={myPlatform}
              sharedLayout={false}
              onSend={(x) => openSend({ song: songFromCard(x) })}
            />
          ) : (
            <EmptyState
              pose="idle"
              title={
                connections.data?.some((c) => c.status === "CONNECTED")
                  ? "Play something on any app"
                  : "Connect your music"
              }
              action={
                connections.data?.some((c) => c.status === "CONNECTED")
                  ? undefined
                  : {
                      label: "Connect your music",
                      onClick: () => router.push("/settings/connections"),
                    }
              }
            />
          )}
        </div>
      </section>
    </div>
  );
}

/**
 * A brand-new account's Home: two honest steps, nothing borrowed from anyone else. Charts, the
 * Now stage and the reveal appear only once there are real people and real plays behind them.
 */
function GetStarted({ connected }: { connected: boolean }) {
  const steps = [
    {
      done: connected,
      title: "Connect your music",
      body: "One tap: Spotify, Apple Music, YouTube Music or Amazon Music.",
      href: "/settings/connections",
      cta: "Connect",
    },
    {
      done: false,
      title: "Add your friends",
      body: "Share your invite link. Home fills up with what they're playing.",
      href: "/friends?tab=find",
      cta: "Invite friends",
    },
  ];
  return (
    <section
      aria-labelledby="start-h"
      className="rounded-[24px] border border-border bg-surface-1 p-6"
    >
      <h2
        id="start-h"
        className="font-display text-2xl font-semibold tracking-tight"
      >
        Get started
      </h2>
      <ol className="mt-4 flex flex-col gap-3">
        {steps.map((st, i) => (
          <li
            key={st.title}
            className="flex items-center gap-4 rounded-[16px] bg-surface-2 p-4"
          >
            <span
              aria-hidden
              className={`grid h-8 w-8 shrink-0 place-items-center rounded-full font-mono text-sm ${st.done ? "bg-success text-bg" : "border border-border-strong"}`}
            >
              {st.done ? "✓" : i + 1}
            </span>
            <div className="min-w-0 flex-1">
              <p className="font-semibold">
                {st.title}
                {st.done && <span className="sr-only"> (done)</span>}
              </p>
              <p className="text-sm text-text-muted">{st.body}</p>
            </div>
            {!st.done && (
              <Link
                href={st.href}
                className="shrink-0 rounded-pill bg-text px-4 py-2 text-sm font-semibold text-bg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus-ring)]"
              >
                {st.cta}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
