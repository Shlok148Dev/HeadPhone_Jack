"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PLATFORM_NAMES, type Platform } from "@/components/ds";
import { api, json } from "./api";
import type { Person } from "./social";

export type SendStatus = "sent" | "delivered" | "viewed" | "played";
export const STATUSES: SendStatus[] = ["sent", "delivered", "viewed", "played"];
export const REACTIONS = ["🔥", "❤️", "😂", "🤯", "👀", "🙌"] as const;
export const NOTE_MAX = 280;
export const MIXTAPE_MIN = 5;
export const MIXTAPE_MAX = 8;

export interface Song {
  recording_id: string | null;
  title: string;
  artist: string;
  links?: Partial<Record<Platform, string | null>>;
  search_links?: Partial<Record<Platform, string>>;
}

export interface Received {
  id: string;
  kind: "track" | "mixtape";
  sender: Person;
  note: string;
  items: Song[];
  circle: { id: string; name: string } | null;
  sent_at: string;
  status: SendStatus;
  reaction: string;
  is_reply: boolean;
}

export interface Sent {
  id: string;
  kind: "track" | "mixtape";
  note: string;
  items: Song[];
  sent_at: string;
  recipients: { user: Person; status: SendStatus; reaction: string; credit_artist: string | null }[];
}

/**
 * JNG-06-03: open a sent song on *my* platform. A verified link deep-links; otherwise say
 * "Not found on {Platform}" and offer a search there. Never names how the song was captured.
 */
export function openTarget(song: Song, mine: Platform | undefined): { url: string; label: string; notFound: string | null } | null {
  const links = song.links ?? {};
  const search = song.search_links ?? {};
  if (mine && mine !== "UNKNOWN") {
    const name = PLATFORM_NAMES[mine];
    if (links[mine]) return { url: links[mine] as string, label: `Open in ${name}`, notFound: null };
    if (search[mine]) return { url: search[mine] as string, label: `Search in ${name}`, notFound: `Not found on ${name}` };
  }
  for (const [p, url] of Object.entries(links)) if (url) return { url, label: `Open in ${PLATFORM_NAMES[p as Exclude<Platform, "UNKNOWN">]}`, notFound: null };
  return null;
}

export const useInbox = (enabled = true) =>
  useQuery({ queryKey: ["inbox", "received"], queryFn: () => api<Received[]>("/inbox"), enabled });
export const useSent = (enabled = true) =>
  useQuery({ queryKey: ["inbox", "sent"], queryFn: () => api<Sent[]>("/inbox/sent"), enabled });
export const useUnread = () =>
  useQuery({ queryKey: ["inbox", "unread"], queryFn: () => api<{ count: number }>("/inbox/unread"), refetchInterval: 60_000 });
export const useSongSearch = (q: string) =>
  useQuery({
    queryKey: ["songs", q],
    queryFn: () => api<Song[]>(`/songs/search?q=${encodeURIComponent(q)}`),
    enabled: q.trim().length >= 2,
    staleTime: 60_000,
  });

export interface SendInput {
  items: { recording_id?: string | null; title: string; artist: string }[];
  note?: string;
  user_ids?: string[];
  circle_ids?: string[];
  reply_to?: string;
}

export function useSendActions() {
  const qc = useQueryClient();
  const refresh = () => void qc.invalidateQueries({ queryKey: ["inbox"] });
  return {
    send: useMutation({
      mutationFn: (b: SendInput) => api<{ id: string; recipients: number }>("/recommendations", { method: "POST", ...json(b) }),
      onSuccess: refresh,
    }),
    view: useMutation({ mutationFn: (id: string) => api<Received>(`/inbox/${id}/view`, { method: "POST" }), onSuccess: refresh }),
    react: useMutation({
      mutationFn: (b: { id: string; reaction: string }) => api<Received>(`/inbox/${b.id}/react`, { method: "POST", ...json({ reaction: b.reaction }) }),
      onSuccess: refresh,
    }),
  };
}
