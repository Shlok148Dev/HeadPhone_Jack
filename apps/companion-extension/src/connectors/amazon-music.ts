import { buildState, findMediaElement, isPlayingFrom, mediaTiming, readSessionMeta, type Connector } from "./common";

/** Amazon Music's web player is served per region; each is the same app. */
export const AMAZON_MUSIC_HOSTS = [
  "music.amazon.com",
  "music.amazon.in",
  "music.amazon.co.uk",
  "music.amazon.de",
  "music.amazon.fr",
  "music.amazon.it",
  "music.amazon.es",
  "music.amazon.ca",
  "music.amazon.com.au",
  "music.amazon.co.jp",
  "music.amazon.com.br",
  "music.amazon.com.mx",
] as const;

/**
 * Amazon Music web player.
 * Primary: MediaSession metadata/playbackState + the page's media element.
 * No DOM selectors are needed. The page URL is not a stable per-track link, so no origin URL.
 */
export const amazonMusic: Connector = {
  platform: "AMAZON_MUSIC",
  hosts: AMAZON_MUSIC_HOSTS,
  read(env) {
    const { doc, mediaSession } = env;
    const meta = readSessionMeta(mediaSession);
    if (!meta) return null;
    const el = findMediaElement(doc);
    return buildState("AMAZON_MUSIC", meta, mediaTiming(el), isPlayingFrom(el, mediaSession));
  },
};
