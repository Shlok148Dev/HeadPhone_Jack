"use client";

import { useQuery } from "@tanstack/react-query";
import type { FeedCardData } from "@/components/ds";
import { api } from "./api";

export interface Feed {
  results: FeedCardData[];
  live_count: number;
  degraded: boolean;
  next_cursor: string | null;
}

const RANK: Record<string, number> = { LIVE: 0, RECENT: 1, TOP: 2, HIDDEN: 3 };
export const LIVE_MAX_AGE_MS = 90_000;

/** BR-02 order, same as the server: Live → newest Recent → Top → Hidden. */
export function sortFeed(cards: FeedCardData[]): FeedCardData[] {
  const ts = (c: FeedCardData) => (c.observed_at ? Date.parse(c.observed_at) : 0);
  return [...cards].sort(
    (a, b) =>
      (RANK[a.state] ?? 9) - (RANK[b.state] ?? 9) ||
      ts(b) - ts(a) ||
      a.friend.display_name.localeCompare(b.friend.display_name),
  );
}

/**
 * Client-side BR-01 guard (UX_SPEC §5.4): never keep showing Live past 90 s since `observed_at`
 * while waiting for the next update. Cards without a time are trusted to the server.
 */
export function isFreshLive(card: FeedCardData, now = Date.now()): boolean {
  if (card.state !== "LIVE") return false;
  if (!card.observed_at) return true;
  return now - Date.parse(card.observed_at) < LIVE_MAX_AGE_MS;
}

export function useFeed(realtime: boolean) {
  return useQuery({
    queryKey: ["feed"],
    queryFn: () => api<Feed>("/feed"),
    // Realtime hints keep it fresh; poll slowly as a safety net, faster when disconnected.
    refetchInterval: realtime ? 60_000 : 15_000,
  });
}
