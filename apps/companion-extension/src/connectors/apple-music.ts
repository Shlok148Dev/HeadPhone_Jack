import { buildState, findMediaElement, isPlayingFrom, mediaTiming, readSessionMeta, type Connector, type ReadEnv } from "./common";

const fold = (s: string): string =>
  s
    .normalize("NFKC")
    .replace(/[‎‏‪-‮]/g, "")
    .trim()
    .toLowerCase();

/**
 * The page URL is used as origin_url only when the user is on the song page of the track that is
 * actually playing (page title starts with the playing title and mentions the artist), and only
 * as origin + pathname. Browsing another song page while music plays yields no origin_url, so no
 * browsing activity is sent.
 */
export function appleSongUrl(env: ReadEnv, title: string, artist: string): string | undefined {
  let url: URL;
  try {
    url = new URL(env.location.href);
  } catch {
    return undefined;
  }
  if (url.hostname !== "music.apple.com" || !/^\/[a-z]{2}\/song\/[^/]+\/\d+\/?$/.test(url.pathname)) return undefined;
  const pageTitle = fold(env.doc.title);
  if (!pageTitle.startsWith(fold(title)) || !pageTitle.includes(fold(artist))) return undefined;
  return url.origin + url.pathname;
}

/**
 * Apple Music web player (music.apple.com).
 * MusicKit JS sets MediaSession metadata and plays through a page <audio> element,
 * so no DOM selectors are needed.
 */
export const appleMusic: Connector = {
  platform: "APPLE_MUSIC",
  hosts: ["music.apple.com"],
  read(env) {
    const { doc, mediaSession } = env;
    const meta = readSessionMeta(mediaSession);
    if (!meta) return null;
    const el = findMediaElement(doc);
    return buildState("APPLE_MUSIC", meta, mediaTiming(el), isPlayingFrom(el, mediaSession), appleSongUrl(env, meta.title, meta.artist));
  },
};
