import type { Platform } from "@/components/ds";

/** The four music apps Jingle connects. The Connect screen itself is ConnectMusic (D-CONNECT-01). */
export type MusicPlatform = Exclude<Platform, "UNKNOWN">;

export const PLATFORMS: MusicPlatform[] = [
  "SPOTIFY",
  "APPLE_MUSIC",
  "YOUTUBE_MUSIC",
  "AMAZON_MUSIC",
];

const NAMES: Record<MusicPlatform, string> = {
  SPOTIFY: "Spotify",
  APPLE_MUSIC: "Apple Music",
  YOUTUBE_MUSIC: "YouTube Music",
  AMAZON_MUSIC: "Amazon Music",
};

export function platformName(p: MusicPlatform): string {
  return NAMES[p];
}
