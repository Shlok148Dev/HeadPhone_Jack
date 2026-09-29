"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { EmptyState, ErrorState, FeedCard, FeedCardSkeleton } from "@/components/ds";
import { useAuth } from "@/lib/auth";
import { useConnections, useMyCard } from "@/lib/queries";

function greeting(now = new Date()): string {
  const h = now.getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

/**
 * Home (UX_SPEC §5.4), Sprint 1 slice: my own card (JNG-05-01) and the no-friends empty state
 * (JNG-05-08). Friends' shelves arrive with the social graph and feed (Sprints 3–4).
 */
export default function HomePage() {
  const { me } = useAuth();
  const router = useRouter();
  const card = useMyCard();
  const connections = useConnections();
  const hasConnection = connections.data?.some((c) => c.status === "CONNECTED") ?? false;
  const empty = card.data && (card.data.state === "HIDDEN" || !card.data.recording);

  return (
    <div className="flex flex-col gap-8">
      <h1 className="font-display text-3xl font-semibold tracking-tight md:text-4xl">
        {greeting()}, {me?.display_name || me?.username}
      </h1>

      <section aria-labelledby="you-heading" className="flex flex-col gap-3">
        <div className="flex items-baseline justify-between">
          <h2 id="you-heading" className="font-display text-xl font-semibold">
            You right now
          </h2>
          <Link href="/settings/connections" className="text-sm text-text-muted underline-offset-4 hover:text-text hover:underline">
            Your music apps
          </Link>
        </div>
        <div className="w-full max-w-[240px] sm:max-w-[280px]">
          {card.isLoading ? (
            <FeedCardSkeleton />
          ) : card.isError ? (
            <ErrorState message="We couldn't load what you're playing." onRetry={() => void card.refetch()} retrying={card.isFetching} />
          ) : empty || !card.data ? (
            <EmptyState
              pose={hasConnection ? "idle" : "wave"}
              title={hasConnection ? "Play something on any app" : "Connect your music"}
              description={
                hasConnection
                  ? "When you play in your connected app, it shows up here for you and your friends."
                  : "Connect the app you listen on, and what you play shows up here."
              }
              action={hasConnection ? undefined : { label: "Connect your music", onClick: () => router.push("/onboarding/sources") }}
            />
          ) : (
            <FeedCard card={card.data} sharedLayout={false} />
          )}
        </div>
      </section>

      <section aria-labelledby="friends-heading" className="rounded-lg border border-border bg-surface-1">
        <h2 id="friends-heading" className="sr-only">
          Friends
        </h2>
        <EmptyState
          pose="wave"
          title="Your feed is waiting for friends"
          description="Soon you'll add friends and see what they're playing here, live."
        />
      </section>
    </div>
  );
}
