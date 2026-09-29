import type { PlatformId, TrackState } from "../shared/types";

/** The subset of the standard Media Session API we read. */
export interface MediaSessionLike {
  metadata: {
    title: string;
    artist: string;
    album: string;
    artwork: ReadonlyArray<{ src: string; sizes?: string }>;
  } | null;
  playbackState: "none" | "paused" | "playing";
}

/** Everything a connector may look at: the open page only. Injected so tests can use fixtures. */
export interface ReadEnv {
  doc: Document;
  mediaSession: MediaSessionLike | undefined;
  location: { href: string; hostname: string; search: string; origin: string };
}

export interface Connector {
  platform: PlatformId;
  /** Hostnames this connector handles (exact match). */
  hosts: readonly string[];
  read(env: ReadEnv): TrackState | null;
}

export function browserEnv(): ReadEnv {
  return {
    doc: document,
    mediaSession: (navigator as Navigator & { mediaSession?: MediaSessionLike }).mediaSession,
    location: window.location,
  };
}

export interface SessionMeta {
  title: string;
  artist: string;
  album?: string;
  artworkUrl?: string;
}

const clean = (s: string | null | undefined): string => (s ?? "").replace(/\s+/g, " ").trim();

export function readSessionMeta(ms: MediaSessionLike | undefined): SessionMeta | null {
  const md = ms?.metadata;
  if (!md) return null;
  const title = clean(md.title);
  if (!title) return null;
  const album = clean(md.album);
  return {
    title,
    artist: clean(md.artist),
    ...(album ? { album } : {}),
    ...(pickArtwork(md.artwork) ? { artworkUrl: pickArtwork(md.artwork) } : {}),
  };
}

/** Largest artwork by its `sizes` hint; https only. */
export function pickArtwork(art: ReadonlyArray<{ src: string; sizes?: string }> | undefined): string | undefined {
  if (!art || art.length === 0) return undefined;
  let best: { src: string; area: number } | undefined;
  for (const a of art) {
    if (!/^https:\/\//.test(a.src)) continue;
    const m = /(\d+)x(\d+)/i.exec(a.sizes ?? "");
    const area = m ? Number(m[1]) * Number(m[2]) : 0;
    if (!best || area >= best.area) best = { src: a.src, area };
  }
  return best?.src;
}

/** The page's own media element: the one playing, else the one with a known duration. */
export function findMediaElement(doc: Document): HTMLMediaElement | null {
  const els = Array.from(doc.querySelectorAll<HTMLMediaElement>("video, audio"));
  const playing = els.find((e) => !e.paused && !e.ended);
  if (playing) return playing;
  return els.find((e) => Number.isFinite(e.duration) && e.duration > 0) ?? null;
}

export function mediaTiming(el: HTMLMediaElement | null): { durationMs?: number; positionMs?: number } {
  if (!el) return {};
  const out: { durationMs?: number; positionMs?: number } = {};
  if (Number.isFinite(el.duration) && el.duration > 0) out.durationMs = Math.round(el.duration * 1000);
  if (Number.isFinite(el.currentTime) && el.currentTime >= 0) out.positionMs = Math.round(el.currentTime * 1000);
  return out;
}

/** Playing state: the media element is authoritative, then MediaSession.playbackState. */
export function isPlayingFrom(el: HTMLMediaElement | null, ms: MediaSessionLike | undefined, fallback?: boolean): boolean {
  if (el) return !el.paused && !el.ended;
  if (ms && ms.playbackState !== "none") return ms.playbackState === "playing";
  return fallback ?? false;
}

/** "3:45" | "1:02:03" | "-0:42" → ms (sign preserved). */
export function parseClock(text: string | null | undefined): number | undefined {
  const t = clean(text);
  const m = /^(-)?(\d+):(\d{2})(?::(\d{2}))?$/.exec(t);
  if (!m) return undefined;
  const parts = [m[2], m[3], m[4]].filter((x): x is string => x !== undefined).map(Number);
  let secs = 0;
  for (const p of parts) secs = secs * 60 + p;
  return (m[1] ? -1 : 1) * secs * 1000;
}

export function textOf(doc: Document, selector: string): string | undefined {
  const t = clean(doc.querySelector(selector)?.textContent);
  return t || undefined;
}

/** Page-supplied text is capped before it leaves the page. */
export const MAX_TEXT = 512;
export const MAX_URL = 2048;
/** Longer than a day is not a track (live streams report Infinity or huge values). */
const MAX_DURATION_MS = 24 * 3600_000;

const cap = (s: string): string => (s.length > MAX_TEXT ? s.slice(0, MAX_TEXT) : s);

/** Build a TrackState, dropping empty optional fields and capping page-supplied values. */
export function buildState(
  platform: PlatformId,
  meta: SessionMeta,
  timing: { durationMs?: number; positionMs?: number },
  isPlaying: boolean,
  originUrl?: string,
): TrackState | null {
  if (!meta.title || !meta.artist) return null;
  const s: TrackState = { platform, artist: cap(meta.artist), title: cap(meta.title), isPlaying };
  if (meta.album) s.album = cap(meta.album);
  if (timing.durationMs !== undefined && timing.durationMs <= MAX_DURATION_MS) s.durationMs = timing.durationMs;
  if (timing.positionMs !== undefined && timing.positionMs <= MAX_DURATION_MS) s.positionMs = timing.positionMs;
  if (originUrl && originUrl.length <= MAX_URL) s.originUrl = originUrl;
  if (meta.artworkUrl && meta.artworkUrl.length <= MAX_URL) s.artworkUrl = meta.artworkUrl;
  return s;
}
