import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ArtworkColors, Platform } from "@/components/ds";
import { api, json } from "@/lib/api";
import type { Person } from "@/lib/social";

export interface Drop {
  id: string;
  user: Person;
  title: string;
  artist: string;
  note: string;
  created_at: string;
  links: Partial<Record<Platform, string | null>>;
  search_links: Partial<Record<Platform, string>>;
  artwork_url: string | null;
  artwork_small: string | null;
  artwork_colors: ArtworkColors | null;
}

export interface DropsToday {
  day: string;
  mine: Drop | null;
  streak: number;
  /** true until you drop: friends' songs stay hidden, only who dropped is shown. */
  locked: boolean;
  friends: Drop[];
  dropped: Person[];
}

export const useDropsToday = (enabled = true) =>
  useQuery({ queryKey: ["drops", "today"], queryFn: () => api<DropsToday>("/drops/today"), enabled, refetchInterval: 120_000 });

export function useDropSong() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { title: string; artist: string; note?: string; recording_id?: string | null }) =>
      api<Drop>("/drops", { method: "POST", ...json(input), headers: { "Idempotency-Key": crypto.randomUUID() } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["drops", "today"] }),
  });
}
