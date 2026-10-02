import { PLATFORM_NAMES, type Platform } from "@/components/ds";

/** Anything with per-platform links: feed recordings, songs, drops. */
export interface Tunable {
  links?: Partial<Record<Platform, string | null>> | null;
  search_links?: Partial<Record<Platform, string>> | null;
}

export interface Tune {
  url: string;
  platform: Platform;
  /** true: the exact song in that app; false: a search there (we say "Find", never pretend). */
  exact: boolean;
  /** "Play in Spotify" / "Find in Apple Music". */
  label: string;
}

/**
 * Tune in (D-TUNE-01): whatever app a friend used, open the song in *yours*.
 * Your app's exact link → a search in your app → the friend's app → any exact link.
 */
export function tuneIn(song: Tunable, mine?: Platform | null, source?: Platform | null): Tune | null {
  const links = song.links ?? {};
  const search = song.search_links ?? {};
  const make = (platform: Platform, url: string, exact: boolean): Tune => ({
    url,
    platform,
    exact,
    label: `${exact ? "Play" : "Find"} in ${platform === "UNKNOWN" ? "your app" : PLATFORM_NAMES[platform]}`,
  });
  if (mine && mine in PLATFORM_NAMES) {
    if (links[mine]) return make(mine, links[mine] as string, true);
    if (search[mine]) return make(mine, search[mine] as string, false);
  }
  if (source && source in PLATFORM_NAMES && links[source]) return make(source, links[source] as string, true);
  // Only the four listening apps we can name; other link keys (if any) are ignored.
  for (const [p, url] of Object.entries(links)) if (url && p in PLATFORM_NAMES) return make(p as Platform, url, true);
  if (source && source in PLATFORM_NAMES && search[source]) return make(source, search[source] as string, false);
  return null;
}
