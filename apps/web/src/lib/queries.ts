"use client";

import { useQuery } from "@tanstack/react-query";
import type { FeedCardData, NowPlayingTrack, Platform } from "@/components/ds";
import { api } from "./api";

export interface Connection {
  platform: Exclude<Platform, "UNKNOWN">;
  status: "CONNECTED" | "NEEDS_REAUTH" | "PENDING_FIRST_PLAY" | "ERROR" | "DISABLED";
  first_play_at: string | null;
  last_signal_at: string | null;
  capabilities: { live_on_web: boolean; live_on_phone: boolean; history: boolean };
  note: string;
}

/** My own card (JNG-05-01). Polled until the realtime gateway lands in Sprint 4. */
export function useMyCard(enabled = true) {
  return useQuery({
    queryKey: ["me", "card"],
    queryFn: () => api<FeedCardData>("/me/card"),
    enabled,
    refetchInterval: 15_000,
  });
}

export function useConnections(opts: { poll?: boolean } = {}) {
  return useQuery({
    queryKey: ["connections"],
    queryFn: () => api<Connection[]>("/connections"),
    refetchInterval: opts.poll ? 3_000 : false,
  });
}

export function toNowPlaying(card: FeedCardData | undefined): NowPlayingTrack | null {
  if (!card || !card.recording || card.state === "HIDDEN") return null;
  return {
    id: card.recording.id,
    title: card.recording.title,
    artist: card.recording.artist,
    artwork_url: card.recording.artwork_url,
    platform: card.platform,
    state: card.state,
    freshness_label: card.freshness_label,
  };
}
