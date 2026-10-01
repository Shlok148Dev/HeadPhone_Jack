"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { api, json } from "./api";
import type { Person } from "./social";
import type { Song } from "./sends";
import { useSocket } from "./realtime";

// ---- Blends (JNG-07-01…04) -----------------------------------------------------------------

export interface BlendTrack extends Song {
  id: number;
  reason: string;
  pinned: boolean;
}

export interface Blend {
  id: string;
  name: string;
  circle: { id: string; name: string } | null;
  members: Person[];
  left_out: Person[];
  generated_at: string | null;
  track_count: number;
  covers: string[];
  tracks?: BlendTrack[];
  save: { available: boolean; message: string };
}

export const useBlends = () => useQuery({ queryKey: ["blends"], queryFn: () => api<Blend[]>("/blends") });
export const useBlend = (id: string) => useQuery({ queryKey: ["blends", id], queryFn: () => api<Blend>(`/blends/${id}`) });

export function useBlendActions() {
  const qc = useQueryClient();
  const put = (b: Blend) => {
    qc.setQueryData(["blends", b.id], b);
    void qc.invalidateQueries({ queryKey: ["blends"], exact: true });
  };
  return {
    create: useMutation({
      mutationFn: (b: { user_ids?: string[]; circle_id?: string; name?: string }) => api<Blend>("/blends", { method: "POST", ...json(b) }),
      onSuccess: put,
    }),
    regenerate: useMutation({ mutationFn: (id: string) => api<Blend>(`/blends/${id}/regenerate`, { method: "POST" }), onSuccess: put }),
    pin: useMutation({
      mutationFn: (b: { blendId: string; trackId: number; on: boolean }) =>
        api<BlendTrack>(`/blends/${b.blendId}/tracks/${b.trackId}/pin`, { method: b.on ? "POST" : "DELETE" }),
      onSuccess: (t, b) =>
        qc.setQueryData<Blend>(["blends", b.blendId], (prev) =>
          prev ? { ...prev, tracks: prev.tracks?.map((x) => (x.id === t.id ? { ...x, pinned: t.pinned } : x)) } : prev,
        ),
    }),
    leave: useMutation({
      mutationFn: (id: string) => api(`/blends/${id}`, { method: "DELETE" }),
      onSuccess: () => void qc.invalidateQueries({ queryKey: ["blends"] }),
    }),
  };
}

// ---- Live sessions (JNG-07-05…09) ----------------------------------------------------------

export interface SessionPerson {
  id: string;
  username: string;
  display_name: string;
}

export interface QueueEntry {
  id: string;
  recording_id: string | null;
  title: string;
  artist: string;
  added_by: SessionPerson | null;
  score: number;
  artwork_url?: string | null;
  artwork_small?: string | null;
  artwork_colors?: import("@/components/ds").ArtworkColors | null;
}

export interface SessionState {
  id: string;
  title: string;
  host: SessionPerson;
  ended: boolean;
  now_playing: QueueEntry | null;
  queue: QueueEntry[];
  participants: (SessionPerson & { online: boolean })[];
  version: number;
  my_votes: Record<string, number>;
  joined: boolean;
  now_playing_links: { links: Song["links"]; search_links: Song["search_links"] } | null;
}

export interface SessionSummary {
  id: string;
  title: string;
  host: SessionPerson;
  circle: { id: string; name: string } | null;
  joined: boolean;
  participant_count: number;
}

export const useSessions = () =>
  useQuery({ queryKey: ["sessions"], queryFn: () => api<SessionSummary[]>("/sessions"), refetchInterval: 30_000 });

const sessionKey = (id: string) => ["session", id] as const;

/**
 * Apply a room broadcast. Deltas carry the room's public state with a monotonically increasing
 * version: older or equal versions are ignored; my own votes are kept (they're per viewer).
 * Returns null when the delta can't be applied locally and a REST refetch is needed.
 */
export function applyDelta(prev: SessionState | undefined, version: number, state: Omit<SessionState, "version" | "my_votes" | "joined" | "now_playing_links">): SessionState | null {
  if (!prev) return null;
  if (version <= prev.version) return prev;
  const ids = new Set(state.queue.map((e) => e.id));
  const my_votes = Object.fromEntries(Object.entries(prev.my_votes).filter(([k]) => ids.has(k)));
  if ((state.now_playing?.id ?? null) !== (prev.now_playing?.id ?? null)) return null; // needs fresh links
  return { ...prev, ...state, version, my_votes };
}

export function useSession(id: string) {
  const qc = useQueryClient();
  const socket = useSocket();
  const q = useQuery({
    queryKey: sessionKey(id),
    queryFn: async () => {
      const s = await api<SessionState>(`/sessions/${id}`);
      // A refetch mustn't undo taps still on their way to the server.
      const my_votes = { ...s.my_votes };
      for (const [entry, v] of intended) if (v) my_votes[entry] = v; else delete my_votes[entry];
      return { ...s, my_votes };
    },
  });
  const joined = q.data?.joined ?? false;

  // JNG-07-09: (re)join the room on every connect, then catch up over REST.
  useEffect(() => {
    if (!socket || !joined) return;
    const join = () => {
      socket.emit("session:join", { session_id: id });
      void qc.invalidateQueries({ queryKey: sessionKey(id) });
    };
    const onDelta = (msg: { session_id: string; version: number; state: SessionState }) => {
      if (msg.session_id !== id) return;
      const prev = qc.getQueryData<SessionState>(sessionKey(id));
      const next = applyDelta(prev, msg.version, msg.state);
      if (next) qc.setQueryData(sessionKey(id), next);
      else void qc.invalidateQueries({ queryKey: sessionKey(id) });
    };
    if (socket.connected) join();
    socket.on("connect", join);
    socket.on("queue:delta", onDelta);
    return () => {
      socket.off("connect", join);
      socket.off("queue:delta", onDelta);
      socket.emit("session:leave", { session_id: id });
    };
  }, [socket, joined, id, qc]);
  return q;
}

// Votes on one entry go out in order: rapid toggles must land as tapped, not as the network
// happens to deliver them (the server keeps the last write).
const voteChains = new Map<string, Promise<unknown>>();
const intended = new Map<string, number>(); // my latest tap per entry while requests are in flight
function chainVote<T>(entryId: string, value: number, send: () => Promise<T>): Promise<T> {
  intended.set(entryId, value);
  const prev = voteChains.get(entryId) ?? Promise.resolve();
  const next = prev.catch(() => undefined).then(send);
  voteChains.set(entryId, next);
  void next.finally(() => {
    if (voteChains.get(entryId) === next) {
      voteChains.delete(entryId);
      intended.delete(entryId);
    }
  });
  return next;
}

export function useSessionActions(id: string) {
  const qc = useQueryClient();
  const set = (s: SessionState) => qc.setQueryData(sessionKey(id), s);
  const refresh = () => void qc.invalidateQueries({ queryKey: sessionKey(id) });
  return {
    join: useMutation({ mutationFn: () => api<SessionState>(`/sessions/${id}/join`, { method: "POST" }), onSuccess: set }),
    leave: useMutation({
      mutationFn: () => api<SessionState>(`/sessions/${id}/leave`, { method: "POST" }),
      onSuccess: () => void qc.invalidateQueries({ queryKey: ["sessions"] }),
    }),
    next: useMutation({ mutationFn: () => api<SessionState>(`/sessions/${id}/next`, { method: "POST" }), onSuccess: set }),
    end: useMutation({ mutationFn: () => api<SessionState>(`/sessions/${id}/end`, { method: "POST" }), onSuccess: set }),
    add: useMutation({
      mutationFn: (b: { recording_id?: string | null; title: string; artist: string; anonymous: boolean }) =>
        api<QueueEntry>(`/sessions/${id}/queue`, {
          method: "POST",
          ...json({ ...b, idempotency_key: crypto.randomUUID() }),
        }),
      onSuccess: refresh,
    }),
    vote: useMutation({
      mutationFn: (b: { entryId: string; value: 1 | -1 | 0 }) =>
        chainVote(b.entryId, b.value, () => api<QueueEntry>(`/queue/${b.entryId}/vote`, { method: "POST", ...json({ value: b.value }) })),
      onMutate: (b) =>
        qc.setQueryData<SessionState>(sessionKey(id), (prev) =>
          prev ? { ...prev, my_votes: { ...prev.my_votes, [b.entryId]: b.value } } : prev,
        ),
      onError: refresh,
    }),
  };
}

export function useStartSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (b: { title?: string; user_ids?: string[]; circle_id?: string }) => api<SessionState>("/sessions", { method: "POST", ...json(b) }),
    onSuccess: (s) => {
      qc.setQueryData(sessionKey(s.id), s);
      void qc.invalidateQueries({ queryKey: ["sessions"] });
    },
  });
}
