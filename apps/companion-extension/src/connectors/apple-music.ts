import { buildState, findMediaElement, isPlayingFrom, mediaTiming, readSessionMeta, type Connector } from "./common";

/**
 * Apple Music web player (music.apple.com).
 * MusicKit JS sets MediaSession metadata and plays through a page <audio> element,
 * so no DOM selectors are needed. The origin URL is the page URL when it is a song page.
 */
export const appleMusic: Connector = {
  platform: "APPLE_MUSIC",
  hosts: ["music.apple.com"],
  read(env) {
    const { doc, mediaSession, location } = env;
    const meta = readSessionMeta(mediaSession);
    if (!meta) return null;
    const el = findMediaElement(doc);
    const originUrl = /^https:\/\/music\.apple\.com\/[a-z]{2}\/song\//.test(location.href) ? location.href.split("#")[0] : undefined;
    return buildState("APPLE_MUSIC", meta, mediaTiming(el), isPlayingFrom(el, mediaSession), originUrl);
  },
};
