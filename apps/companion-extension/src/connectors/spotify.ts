import { buildState, findMediaElement, isPlayingFrom, mediaTiming, parseClock, readSessionMeta, type Connector } from "./common";

const SEL = {
  position: '[data-testid="playback-position"]',
  duration: '[data-testid="playback-duration"]',
  trackLink: '[data-testid="now-playing-widget"] a[href*="/track/"], [data-testid="context-item-link"]',
} as const;

/**
 * Spotify web player (open.spotify.com).
 * Primary: MediaSession metadata/playbackState. Spotify's media element is often not attached
 * to the DOM, so position/duration fall back to the player bar's own clock labels.
 */
export const spotify: Connector = {
  platform: "SPOTIFY",
  hosts: ["open.spotify.com"],
  read(env) {
    const { doc, mediaSession } = env;
    const meta = readSessionMeta(mediaSession);
    if (!meta) return null;

    const el = findMediaElement(doc);
    const timing = mediaTiming(el);
    if (timing.durationMs === undefined) {
      const pos = parseClock(doc.querySelector(SEL.position)?.textContent);
      const dur = parseClock(doc.querySelector(SEL.duration)?.textContent);
      if (pos !== undefined && pos >= 0) timing.positionMs = pos;
      // The duration label can be toggled to "remaining" (-m:ss).
      if (dur !== undefined) timing.durationMs = dur >= 0 ? dur : (pos ?? 0) - dur;
    }

    return buildState("SPOTIFY", meta, timing, isPlayingFrom(el, mediaSession), trackUrl(doc));
  },
};

function trackUrl(doc: Document): string | undefined {
  const href = doc.querySelector<HTMLAnchorElement>(SEL.trackLink)?.getAttribute("href");
  if (!href) return undefined;
  let url: URL;
  try {
    url = new URL(href, "https://open.spotify.com");
  } catch {
    return undefined;
  }
  const direct = /^\/track\/([A-Za-z0-9]{22})/.exec(url.pathname);
  const highlighted = /^spotify:track:([A-Za-z0-9]{22})$/.exec(url.searchParams.get("highlight") ?? "");
  const id = direct?.[1] ?? highlighted?.[1];
  return id ? `https://open.spotify.com/track/${id}` : undefined;
}
