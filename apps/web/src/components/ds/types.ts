/** Client-side mirror of CONTRACTS.md §7 FeedCard (ADR-0002: no `via`). */

export type Platform = "SPOTIFY" | "APPLE_MUSIC" | "YOUTUBE_MUSIC" | "AMAZON_MUSIC" | "UNKNOWN";
export type CardState = "LIVE" | "RECENT" | "TOP" | "HIDDEN";

export const PLATFORM_NAMES: Record<Exclude<Platform, "UNKNOWN">, string> = {
  SPOTIFY: "Spotify",
  APPLE_MUSIC: "Apple Music",
  YOUTUBE_MUSIC: "YouTube Music",
  AMAZON_MUSIC: "Amazon Music",
};

export interface FeedFriend {
  id: string;
  username: string;
  display_name: string;
  avatar_url: string | null;
}

export interface FeedRecording {
  id: string | null;
  title: string;
  artist: string;
  album?: string | null;
  artwork_url: string | null;
  /** Real artwork from the Artwork service: a small URL for lists, and colours from the cover. */
  artwork_small?: string | null;
  artwork_colors?: ArtworkColors | null;
  links: Partial<Record<Platform, string | null>>;
  /** Search on each platform when no verified link exists (JNG-06-03). */
  search_links?: Partial<Record<Platform, string>>;
}

export interface ArtworkColors {
  dominant: string;
  accent: string;
  /** Pre-checked: --text reads at ≥ 4.5:1 on these in each theme. */
  ambient_dark: string;
  ambient_light: string;
}

export interface FeedCardData {
  friend: FeedFriend;
  state: CardState;
  platform: Platform;
  recording: FeedRecording | null;
  /** Omitted when the friend hides precise time. */
  observed_at?: string | null;
  /** Server-built label; rendered verbatim. */
  freshness_label: string;
  degraded: boolean;
  attribution: "SPOTIFY" | null;
}
