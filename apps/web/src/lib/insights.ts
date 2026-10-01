"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import type { Person } from "./social";

export interface Factor {
  key: string;
  label: string;
  value: number;
  weight: number;
  detail: string;
}

export interface Compatibility {
  ready: boolean;
  score: number | null;
  calibrated: boolean;
  breakdown: Factor[];
  notes: string[];
  shared_artists: string[];
  shared_genres: string[];
  audio_features_available: boolean;
}

export interface Stats {
  ready: boolean;
  days_of_data: number;
  ready_in_days: number;
  plays_30d?: number;
  minutes_30d?: number;
  top_artists?: { name: string; plays: number }[];
  genres?: { name: string; share: number }[];
  platforms?: { platform: string; share: number }[];
  excluded_note?: string | null;
}

export interface Month {
  month: string;
  plays: number;
  top_artist: string | null;
  genres: { name: string; share: number }[];
}

export interface Profile {
  person: Person;
  is_me: boolean;
  compatibility_available: boolean;
  college: string;
  city: string;
}

export const useProfile = (username: string) =>
  useQuery({ queryKey: ["profile", username], queryFn: () => api<Profile>(`/users/${encodeURIComponent(username)}`), retry: false });
export const useMyStats = (enabled: boolean) => useQuery({ queryKey: ["me", "stats"], queryFn: () => api<Stats>("/me/stats"), enabled });
export const useTimeline = (enabled: boolean) => useQuery({ queryKey: ["me", "timeline"], queryFn: () => api<Month[]>("/me/timeline"), enabled });
export const useCompatibility = (userId: string | undefined, enabled: boolean) =>
  useQuery({ queryKey: ["compat", userId], queryFn: () => api<Compatibility>(`/compatibility/${userId}`), enabled: enabled && !!userId });

export function monthLabel(m: string): string {
  const [y, mo] = m.split("-").map(Number);
  return new Date(Date.UTC(y!, (mo ?? 1) - 1, 1)).toLocaleString("en", { month: "short", timeZone: "UTC" });
}
