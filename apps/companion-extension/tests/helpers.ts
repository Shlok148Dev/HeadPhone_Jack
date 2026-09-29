import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { MediaSessionLike, ReadEnv } from "../src/connectors/common";

export function loadFixture(name: string): void {
  document.body.innerHTML = readFileSync(resolve(__dirname, "fixtures", name), "utf8");
}

/** Hand-written stand-in for navigator.mediaSession. */
export function mediaSession(
  md: { title: string; artist: string; album?: string; artwork?: { src: string; sizes?: string }[] } | null,
  playbackState: MediaSessionLike["playbackState"] = "playing",
): MediaSessionLike {
  return {
    metadata: md ? { title: md.title, artist: md.artist, album: md.album ?? "", artwork: md.artwork ?? [] } : null,
    playbackState,
  };
}

/** jsdom media elements have no playback; set the fields a real page would. */
export function setMedia(selector: string, v: { currentTime?: number; duration?: number; paused?: boolean }): void {
  const el = document.querySelector<HTMLMediaElement>(selector);
  if (!el) throw new Error(`no ${selector} in fixture`);
  if (v.currentTime !== undefined) Object.defineProperty(el, "currentTime", { value: v.currentTime, configurable: true });
  if (v.duration !== undefined) Object.defineProperty(el, "duration", { value: v.duration, configurable: true });
  if (v.paused !== undefined) Object.defineProperty(el, "paused", { value: v.paused, configurable: true });
}

export function env(ms: MediaSessionLike | undefined, href: string): ReadEnv {
  const u = new URL(href);
  return { doc: document, mediaSession: ms, location: { href: u.href, hostname: u.hostname, search: u.search, origin: u.origin } };
}
