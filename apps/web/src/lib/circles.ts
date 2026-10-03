"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ArtworkColors, FeedCardData, Platform } from "@/components/ds";
import { api, json } from "./api";
import type { Person } from "./social";

export type Role = "owner" | "admin" | "member";

export interface Circle {
  id: string;
  name: string;
  visibility: "private" | "discoverable";
  member_count: number;
  my_role: Role | null;
  members_can_invite: boolean;
  battle_schedule: Record<string, string | null>;
  members?: { user: Person; role: Role }[];
  /** Songs in the circle's shared playlist (detail only). */
  playlist_count?: number;
  /** Real covers of what members played, through the viewer's privacy view (list only). */
  covers?: string[];
}

export interface CircleInvite {
  id: string;
  circle: { id: string; name: string; member_count: number };
  from: Person;
}

export interface SuggestedCircle {
  id: string;
  name: string;
  members: Person[];
}

export const useCircles = () => useQuery({ queryKey: ["circles"], queryFn: () => api<Circle[]>("/circles") });
export const useCircle = (id: string) => useQuery({ queryKey: ["circles", id], queryFn: () => api<Circle>(`/circles/${id}`) });
export const useCircleFeed = (id: string) =>
  useQuery({ queryKey: ["feed", "circle-page", id], queryFn: () => api<FeedCardData[]>(`/circles/${id}/feed`), refetchInterval: 60_000 });
export const useCircleInvites = () => useQuery({ queryKey: ["circles", "invites"], queryFn: () => api<CircleInvite[]>("/circles/invites") });
export const useSuggestedCircles = () => useQuery({ queryKey: ["circles", "suggested"], queryFn: () => api<SuggestedCircle[]>("/circles/suggested") });

export function useCircleActions() {
  const qc = useQueryClient();
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ["circles"] });
    void qc.invalidateQueries({ queryKey: ["feed"] });
  };
  const m = <A, R = unknown>(fn: (a: A) => Promise<R>) => useMutation({ mutationFn: fn, onSuccess: refresh });
  return {
    create: m((b: { name: string; visibility: string }) => api<Circle>("/circles", { method: "POST", ...json(b) })),
    update: m((b: { id: string; patch: Record<string, unknown> }) => api<Circle>(`/circles/${b.id}`, { method: "PATCH", ...json(b.patch) })),
    leave: m((id: string) => api(`/circles/${id}`, { method: "DELETE" })),
    invite: m((b: { id: string; userIds: string[] }) => api(`/circles/${b.id}/invites`, { method: "POST", ...json({ user_ids: b.userIds }) })),
    link: m((id: string) => api<{ url: string; expires_at: string }>(`/circles/${id}/links`, { method: "POST" })),
    setRole: m((b: { id: string; userId: string; role: Role }) => api(`/circles/${b.id}/members/${b.userId}`, { method: "PATCH", ...json({ role: b.role }) })),
    remove: m((b: { id: string; userId: string }) => api(`/circles/${b.id}/members/${b.userId}`, { method: "DELETE" })),
    transfer: m((b: { id: string; userId: string }) => api(`/circles/${b.id}/transfer`, { method: "POST", ...json({ user_id: b.userId }) })),
    acceptInvite: m((id: string) => api<Circle>(`/circles/invites/${id}/accept`, { method: "POST" })),
    declineInvite: m((id: string) => api(`/circles/invites/${id}/decline`, { method: "POST" })),
    useSuggestion: m((b: { id: string; name: string; userIds: string[] }) =>
      api<Circle>(`/circles/suggested/${b.id}/create`, { method: "POST", ...json({ name: b.name, user_ids: b.userIds }) }),
    ),
    dismissSuggestion: m((id: string) => api(`/circles/suggested/${id}/dismiss`, { method: "POST" })),
  };
}

// ---- Shared playlist (JNG-04-08) -------------------------------------------------------------

export interface PlaylistItem {
  id: string;
  /** Jingle's song key (same song across apps); used to keep exported copies in sync. */
  key: string;
  title: string;
  artist: string;
  note: string;
  added_at: string;
  /** null when the adder has deleted their account ("Former member"). */
  added_by: Person | null;
  can_remove: boolean;
  recording_id: string | null;
  links: Partial<Record<Platform, string | null>>;
  search_links: Partial<Record<Platform, string>>;
  artwork_url?: string | null;
  artwork_small?: string | null;
  artwork_colors?: ArtworkColors | null;
}

export const useCirclePlaylist = (id: string) =>
  useQuery({
    queryKey: ["circles", id, "playlist"],
    queryFn: () => api<{ circle: { id: string; name: string }; items: PlaylistItem[] }>(`/circles/${id}/playlist`),
  });

export function usePlaylistActions(id: string) {
  const qc = useQueryClient();
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ["circles", id, "playlist"] });
    void qc.invalidateQueries({ queryKey: ["circles", id] });
  };
  return {
    add: useMutation({
      mutationFn: (b: { title: string; artist: string; note?: string; recording_id?: string | null }) =>
        api<PlaylistItem>(`/circles/${id}/playlist`, { method: "POST", ...json(b) }),
      onSuccess: refresh,
    }),
    remove: useMutation({
      mutationFn: (itemId: string) => api<null>(`/circles/${id}/playlist/${itemId}`, { method: "DELETE" }),
      onSuccess: refresh,
    }),
  };
}
