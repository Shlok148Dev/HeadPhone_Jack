/** Platform ids use the exact spelling of CONTRACTS.md §4. */
export type PlatformId = "YOUTUBE_MUSIC" | "SPOTIFY" | "APPLE_MUSIC" | "AMAZON_MUSIC";

export const PLATFORMS: readonly PlatformId[] = [
  "YOUTUBE_MUSIC",
  "SPOTIFY",
  "APPLE_MUSIC",
  "AMAZON_MUSIC",
] as const;

/** Display names (text only; no platform logos anywhere in the extension). */
export const PLATFORM_NAMES: Record<PlatformId, string> = {
  YOUTUBE_MUSIC: "YouTube Music",
  SPOTIFY: "Spotify",
  APPLE_MUSIC: "Apple Music",
  AMAZON_MUSIC: "Amazon Music",
};

/**
 * Canonical `additional_info.music_service` value per platform (the web player's host).
 * Amazon's regional hosts (music.amazon.in, .co.uk, ...) all map to music.amazon.com;
 * the real host is still visible in `origin_url`.
 */
export const MUSIC_SERVICE: Record<PlatformId, string> = {
  YOUTUBE_MUSIC: "music.youtube.com",
  SPOTIFY: "open.spotify.com",
  APPLE_MUSIC: "music.apple.com",
  AMAZON_MUSIC: "music.amazon.com",
};

/** What a connector reads from the page the user has open. */
export interface TrackState {
  platform: PlatformId;
  artist: string;
  title: string;
  album?: string;
  durationMs?: number;
  positionMs?: number;
  isPlaying: boolean;
  originUrl?: string;
  artworkUrl?: string;
}

/** Content script → service worker. */
export type ContentMessage =
  | { type: "jingle:track"; state: TrackState | null }
  | { type: "jingle:pair"; token: string };

/** Popup → service worker. */
export type PopupMessage =
  | { type: "popup:status" }
  | { type: "popup:settings"; patch: { origin?: string; paused?: boolean; platforms?: Partial<Record<PlatformId, boolean>> } }
  | { type: "popup:pair"; token: string }
  | { type: "popup:signOut" }
  | { type: "popup:originChanged" };

export interface PairResult {
  ok: boolean;
  userName?: string;
  error?: string;
}

export function trackKey(t: Pick<TrackState, "platform" | "artist" | "title" | "album">): string {
  return [t.platform, t.artist.trim().toLowerCase(), t.title.trim().toLowerCase(), (t.album ?? "").trim().toLowerCase()].join("␟");
}
