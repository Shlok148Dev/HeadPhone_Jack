"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, json } from "./api";
import type { Song } from "./sends";

// ---- Rituals (EP-09) ----------------------------------------------------------------------

export type Phase = "upcoming" | "nominating" | "voting" | "closed" | "skipped";

export interface ResultRow {
  nomination_id: string;
  rank: number;
  votes: number;
  title: string;
  artist: string;
  recording_id: string | null;
  user: { id: string; username: string; display_name: string };
  artwork_url?: string | null;
  artwork_small?: string | null;
}

export interface BattleNomination extends Song {
  id: string;
  mine: boolean;
  my_vote: boolean;
}

export interface Battle {
  id: string;
  circle: { id: string; name: string };
  week: string;
  phase: Phase;
  nominate_opens: string;
  vote_opens: string;
  closes_at: string;
  my_nomination: { title: string; artist: string } | null;
  nomination_count: number;
  nominations: BattleNomination[];
  votes_left: number;
  results: ResultRow[] | null;
  can_skip: boolean;
}

export interface RecapData {
  month: string;
  minutes: number;
  plays: number;
  top_artists: { name: string; plays: number; image_url?: string | null }[];
  top_tracks: { title: string; artist: string; plays: number; artwork_url?: string | null; artwork_small?: string | null; artwork_colors?: import("@/components/ds").ArtworkColors | null }[];
  top_genre: string | null;
  sends: number;
  received: number;
  battle_wins: number;
}

export interface Recap {
  id: string;
  month: string;
  data: RecapData;
  share_url: string | null;
}

export interface Season {
  weeks: number;
  of: number;
  table: { user: { id: string; username: string; display_name: string }; wins: number }[];
}

export const useRituals = () =>
  useQuery({ queryKey: ["rituals"], queryFn: () => api<{ battles: Battle[]; recap: Recap | null }>("/rituals"), refetchInterval: 60_000 });
export const useSeason = (circleId: string, enabled: boolean) =>
  useQuery({ queryKey: ["season", circleId], queryFn: () => api<Season>(`/circles/${circleId}/season`), enabled });

export function useBattleActions() {
  const qc = useQueryClient();
  const refresh = () => void qc.invalidateQueries({ queryKey: ["rituals"] });
  return {
    nominate: useMutation({
      mutationFn: (b: { circleId: string; song: Song }) =>
        api<Battle>(`/circles/${b.circleId}/battle/nominate`, { method: "POST", ...json({ recording_id: b.song.recording_id, title: b.song.title, artist: b.song.artist }) }),
      onSuccess: refresh,
    }),
    vote: useMutation({
      mutationFn: (b: { battleId: string; nominationId: string; on: boolean }) =>
        b.on
          ? api<Battle>(`/battles/${b.battleId}/votes`, { method: "POST", ...json({ nomination_id: b.nominationId }) })
          : api<Battle>(`/battles/${b.battleId}/votes/${b.nominationId}`, { method: "DELETE" }),
      onSuccess: refresh,
    }),
    skip: useMutation({ mutationFn: (circleId: string) => api<Battle>(`/circles/${circleId}/battle/skip`, { method: "POST" }), onSuccess: refresh }),
    share: useMutation({
      mutationFn: (b: { id: string; on: boolean }) => api<Recap>(`/recaps/${b.id}/share`, { method: b.on ? "POST" : "DELETE" }),
      onSuccess: refresh,
    }),
  };
}

// ---- Notifications (EP-11) ----------------------------------------------------------------

export interface AppNotification {
  id: string;
  type: string;
  title: string;
  url: string;
  created_at: string;
  read: boolean;
}

export interface NotificationSettings {
  types: Record<string, { in_app: boolean; push: boolean }>;
  labels: Record<string, string>;
  quiet_start: string;
  quiet_end: string;
  tz: string;
  push_daily_cap: number;
  push_available: boolean;
  push_subscribed: boolean;
}

export const useNotifications = () =>
  useQuery({ queryKey: ["notifications"], queryFn: () => api<{ unread: number; results: AppNotification[] }>("/notifications"), refetchInterval: 60_000 });
export const useNotificationSettings = () =>
  useQuery({ queryKey: ["notification-settings"], queryFn: () => api<NotificationSettings>("/me/notification-settings") });

export function useNotificationActions() {
  const qc = useQueryClient();
  return {
    readAll: useMutation({
      mutationFn: () => api("/notifications/read", { method: "POST", ...json({}) }),
      onSuccess: () => void qc.invalidateQueries({ queryKey: ["notifications"] }),
    }),
    save: useMutation({
      mutationFn: (s: NotificationSettings) => api<NotificationSettings>("/me/notification-settings", { method: "PUT", ...json(s) }),
      onSuccess: (s) => qc.setQueryData(["notification-settings"], s),
    }),
  };
}

function urlBase64ToUint8Array(base64: string): Uint8Array {
  const padded = (base64 + "=".repeat((4 - (base64.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(padded);
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

/** JNG-11-02: push starts only after the browser's own permission prompt says yes. */
export async function enablePush(): Promise<"on" | "denied" | "unsupported" | "unavailable"> {
  if (typeof window === "undefined" || !("serviceWorker" in navigator) || !("PushManager" in window)) return "unsupported";
  const key = await api<{ available: boolean; public_key: string }>("/notifications/push-key");
  if (!key.available) return "unavailable";
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return "denied";
  const reg = await navigator.serviceWorker.register("/sw.js");
  const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(key.public_key) as BufferSource });
  const j = sub.toJSON();
  await api("/me/push-subscription", { method: "POST", ...json({ endpoint: j.endpoint, keys: j.keys }) });
  return "on";
}

export async function disablePush(): Promise<void> {
  if ("serviceWorker" in navigator) {
    const reg = await navigator.serviceWorker.getRegistration("/sw.js");
    const sub = await reg?.pushManager.getSubscription();
    await sub?.unsubscribe();
  }
  await api("/me/push-subscription", { method: "DELETE" });
}

// ---- Moderation (EP-12) -------------------------------------------------------------------

export interface MyAction {
  id: string;
  kind: "warn" | "mute" | "suspend" | "ban";
  reason: string;
  created_at: string;
  expires_at: string | null;
  lifted: boolean;
  appeal: { status: string; note: string } | null;
}

export const useMyModeration = () => useQuery({ queryKey: ["my-moderation"], queryFn: () => api<{ actions: MyAction[] }>("/me/moderation") });

export function useStaff<T>(path: string, enabled = true) {
  return useQuery({ queryKey: ["staff", path], queryFn: () => api<T>(path), enabled });
}
