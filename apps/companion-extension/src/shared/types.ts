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
  | { type: "jingle:pair"; token: string }
  /** Jingle page → extension (via the pairing content script): already connected to this origin? */
  | { type: "jingle:status" };

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

/**
 * Worker-side validation of a TrackState received by message: shape, types and length caps
 * (512 chars for text, 2048 for URLs, https-only URLs). Returns null if unusable.
 */
export function sanitizeTrack(x: unknown): TrackState | null {
  if (typeof x !== "object" || x === null) return null;
  const o = x as Record<string, unknown>;
  const text = (v: unknown): string | undefined => (typeof v === "string" && v.trim() ? v.trim().slice(0, 512) : undefined);
  const num = (v: unknown): number | undefined => (typeof v === "number" && Number.isFinite(v) && v >= 0 && v <= 86_400_000 ? Math.round(v) : undefined);
  const url = (v: unknown): string | undefined => (typeof v === "string" && v.length <= 2048 && /^https:\/\//.test(v) ? v : undefined);
  const platform = o.platform;
  if (typeof platform !== "string" || !(PLATFORMS as readonly string[]).includes(platform)) return null;
  const artist = text(o.artist);
  const title = text(o.title);
  if (!artist || !title || typeof o.isPlaying !== "boolean") return null;
  const s: TrackState = { platform: platform as PlatformId, artist, title, isPlaying: o.isPlaying };
  const album = text(o.album);
  if (album) s.album = album;
  const d = num(o.durationMs);
  if (d !== undefined) s.durationMs = d;
  const p = num(o.positionMs);
  if (p !== undefined) s.positionMs = p;
  const ou = url(o.originUrl);
  if (ou) s.originUrl = ou;
  const au = url(o.artworkUrl);
  if (au) s.artworkUrl = au;
  return s;
}

export function trackKey(t: Pick<TrackState, "platform" | "artist" | "title" | "album">): string {
  return [t.platform, t.artist.trim().toLowerCase(), t.title.trim().toLowerCase(), (t.album ?? "").trim().toLowerCase()].join("␟");
}
