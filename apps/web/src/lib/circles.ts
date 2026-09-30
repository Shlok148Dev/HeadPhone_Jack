"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { FeedCardData } from "@/components/ds";
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
