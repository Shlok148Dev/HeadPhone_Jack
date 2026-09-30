"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, json } from "./api";

export type Relationship = "self" | "friends" | "outgoing" | "incoming" | "none";

export interface Person {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
  relationship: Relationship;
}

export interface FriendRequest {
  id: string;
  direction: "incoming" | "outgoing";
  user: Person;
  created_at: string;
}

export interface Invite {
  code: string;
  url: string;
  qr_svg: string;
}

export const useFriends = () => useQuery({ queryKey: ["friends"], queryFn: () => api<Person[]>("/friends") });

export const useRequests = () =>
  useQuery({ queryKey: ["friends", "requests"], queryFn: () => api<FriendRequest[]>("/friends/requests"), refetchInterval: 30_000 });

export const useSearch = (q: string) =>
  useQuery({
    queryKey: ["users", "search", q],
    queryFn: () => api<Person[]>(`/users/search?q=${encodeURIComponent(q)}`),
    enabled: q.trim().length >= 2,
    staleTime: 5_000,
  });

export const useInvite = () => useQuery({ queryKey: ["invite"], queryFn: () => api<Invite>("/me/invite") });

export const useBlocks = () => useQuery({ queryKey: ["blocks"], queryFn: () => api<Person[]>("/blocks") });

/** All social mutations refresh the same caches so every list agrees. */
export function useSocialActions() {
  const qc = useQueryClient();
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ["friends"] });
    void qc.invalidateQueries({ queryKey: ["users", "search"] });
    void qc.invalidateQueries({ queryKey: ["blocks"] });
    void qc.invalidateQueries({ queryKey: ["feed"] });
  };
  const m = <A,>(fn: (a: A) => Promise<unknown>) => useMutation({ mutationFn: fn, onSuccess: refresh });
  return {
    add: m((userId: string) => api<Person>("/friends/requests", { method: "POST", ...json({ user_id: userId }) })),
    accept: m((requestId: string) => api(`/friends/requests/${requestId}/accept`, { method: "POST" })),
    decline: m((requestId: string) => api(`/friends/requests/${requestId}/decline`, { method: "POST" })),
    cancel: m((requestId: string) => api(`/friends/requests/${requestId}`, { method: "DELETE" })),
    remove: m((userId: string) => api(`/friends/${userId}`, { method: "DELETE" })),
    block: m((userId: string) => api("/blocks", { method: "POST", ...json({ user_id: userId }) })),
    unblock: m((userId: string) => api(`/blocks/${userId}`, { method: "DELETE" })),
    report: m((r: { userId: string; reason: string; details: string }) =>
      api("/reports", { method: "POST", ...json({ target_type: "user", target_id: r.userId, reason: r.reason, details: r.details }) }),
    ),
  };
}
