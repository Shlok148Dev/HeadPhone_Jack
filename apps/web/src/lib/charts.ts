import { useMutation, useQuery } from "@tanstack/react-query";
import type { ArtworkColors, Platform } from "@/components/ds";
import { api } from "@/lib/api";
import type { Person } from "@/lib/social";

export type Movement = { kind: "up" | "down" | "same" | "new"; by: number };

interface Playable {
  title: string | null;
  artist: string | null;
  recording_id: string | null;
  links: Partial<Record<Platform, string | null>>;
  search_links: Partial<Record<Platform, string>>;
  artwork_url?: string | null;
  artwork_small?: string | null;
  artwork_colors?: ArtworkColors | null;
}

export interface ChartSong extends Playable {
  rank: number;
  key: string;
  /** Consecutive weeks in the top 5, this week included. */
  weeks?: number;
  title: string;
  artist: string;
  listeners: number;
  plays: number;
  movement: Movement;
  people: Person[];
  found_first: Person | null;
  you_played: boolean;
}

export interface ChartArtist {
  rank: number;
  key: string;
  weeks?: number;
  name: string;
  listeners: number;
  plays: number;
  movement: Movement;
  people: Person[];
  new_fans: Person[];
  you_listened: boolean;
  top_song: Playable;
  image_url: string | null;
  image_colors: ArtworkColors | null;
}

export interface WeeklyCharts {
  week_start: string;
  week_end: string;
  is_current: boolean;
  updated_at: string | null;
  contributors: number;
  enough: boolean;
  songs: ChartSong[];
  artists: ChartArtist[];
  /** Last week's frozen chart (Monday 06:00 local) and whether its Home reveal is still to play. */
  last_final?: {
    week_start: string;
    week_end: string;
    enough: boolean;
    songs: ChartSong[];
    artists: ChartArtist[];
    reveal_pending: boolean;
  } | null;
}

/** Song and Artist of the Week among your people (JNG-15-01/02). Server-cached; refreshes hourly. */
export const useWeeklyCharts = () =>
  useQuery({ queryKey: ["charts", "weekly"], queryFn: () => api<WeeklyCharts>("/charts/weekly"), staleTime: 5 * 60_000 });

/** Mark a frozen week's reveal as shown (once per week, any device). */
export function useMarkChartSeen() {
  // No refetch here: the reveal stays on screen until dismissed; the next visit reads fresh state.
  return useMutation({
    mutationFn: (week: string) => api<null>(`/charts/weekly/${week}/seen`, { method: "POST" }),
  });
}
