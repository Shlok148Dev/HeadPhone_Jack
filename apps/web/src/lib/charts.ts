import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (week: string) => api<null>(`/charts/weekly/${week}/seen`, { method: "POST" }),
    // Patch the cached chart in place (no refetch, so the open reveal stays until Done) so that
    // leaving Home and coming back never shows a reveal that was already seen.
    onMutate: (week: string) => {
      qc.setQueryData<WeeklyCharts>(["charts", "weekly"], (d) =>
        d?.last_final && d.last_final.week_start === week ? { ...d, last_final: { ...d.last_final, reveal_pending: false } } : d,
      );
    },
  });
}
