import { buildState, findMediaElement, isPlayingFrom, mediaTiming, readSessionMeta, textOf, type Connector } from "./common";

/**
 * YouTube Music web player (music.youtube.com).
 * Primary: MediaSession metadata + the page's <video> element.
 * Fallback (DOM, only if MediaSession has no metadata): the player bar title/byline.
 * Ads are skipped (the player marks them with `.ad-showing`).
 */
export const youtubeMusic: Connector = {
  platform: "YOUTUBE_MUSIC",
  hosts: ["music.youtube.com"],
  read(env) {
    const { doc, mediaSession, location } = env;
    if (doc.querySelector(".ad-showing, .ad-interrupting")) return null;

    let meta = readSessionMeta(mediaSession);
    if (!meta) {
      const title = textOf(doc, "ytmusic-player-bar .title");
      // Byline is "Artist • Album • Year"; the first segment is the artist.
      const byline = textOf(doc, "ytmusic-player-bar .byline");
      const artist = byline?.split("•")[0]?.trim();
      if (!title || !artist) return null;
      meta = { title, artist };
    }

    const el = findMediaElement(doc);
    const videoId = new URLSearchParams(location.search).get("v");
    const originUrl = videoId && /^[\w-]{6,20}$/.test(videoId) ? `https://music.youtube.com/watch?v=${videoId}` : undefined;
    return buildState("YOUTUBE_MUSIC", meta, mediaTiming(el), isPlayingFrom(el, mediaSession), originUrl);
  },
};
