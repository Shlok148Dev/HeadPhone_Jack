/**
 * Shared pieces for "Play in order in your app" (JNG-04-09, D-EXPORT-01). Each exporter creates or
 * updates a copy of the circle playlist inside the listener's own account, from their browser:
 * their app tokens never leave the page and are never sent to Jingle.
 */

export type ExportPlatform = "spotify" | "apple_music" | "youtube_music";

export interface ExportSong {
  key: string; // Jingle's song key (same song across apps)
  title: string;
  artist: string;
  appleId?: string | null; // exact Apple Music catalogue id, when Jingle knows it
}

export interface PriorExport {
  external_id: string;
  url: string;
  track_keys: string[];
}

export interface ExportResult {
  externalId: string;
  url: string;
  /** Songs placed, in order (their keys): stored so the next run updates instead of duplicating. */
  placedKeys: string[];
  missing: ExportSong[];
  /** Songs removed from the circle that this app can't remove from your copy (Apple). */
  stale?: number;
}

export type Progress = (msg: string) => void;

/** Lower-case, accents and featured credits removed, punctuation as spaces (as Jingle's server). */
export function norm(s: string): string {
  return (s || "")
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/\s*[([](feat|ft|with|from|prod)[^)\]]*[)\]]/gi, "")
    .replace(/&/g, " and ")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .split(/\s+/)
    .filter(Boolean)
    .join(" ");
}

const VARIANTS = new Set(["lofi", "lo", "fi", "remix", "sped", "slowed", "reverb", "karaoke", "instrumental", "cover", "live", "version", "acoustic", "mashup", "8d"]);

/** How well a catalogue result matches the song (artist must match; originals beat variants). */
export function score(wantTitle: string, wantArtist: string, title: string, artists: string): number {
  const t = norm(wantTitle);
  const a = norm(wantArtist);
  const rt = norm(title);
  const ra = norm(artists);
  const aw = a.split(" ");
  const artistOk = aw.filter((w) => ra.split(" ").includes(w)).length / Math.max(1, aw.length) >= 0.5;
  if (!artistOk) return 0;
  const tw = t.split(" ");
  const rw = rt.split(" ");
  const overlap = tw.filter((w) => rw.includes(w)).length / Math.max(1, tw.length);
  const extra = rw.filter((w) => !tw.includes(w));
  const variant = extra.filter((w) => VARIANTS.has(w)).length;
  return overlap * 0.7 + (rt === t ? 0.3 : 0) - 0.25 * variant - 0.02 * extra.length;
}

export const MATCH_THRESHOLD = 0.6;

export const playlistName = (circle: string) => `${circle} · Jingle`;
export const playlistDescription = (circle: string) =>
  `The ${circle} circle's shared playlist on Jingle, in order. Updated from Jingle; edits here may be replaced.`;

/** Apple Music catalogue id from a Jingle exact link (https://music.apple.com/song/123). */
export function appleIdFromLink(link?: string | null): string | null {
  const m = link?.match(/music\.apple\.com\/(?:[a-z]{2}\/)?song\/(?:[^/]+\/)?(\d+)/);
  return m ? m[1]! : null;
}

/** Open a centered popup synchronously (inside the click) so browsers allow it. */
export function openPopup(name: string): Window | null {
  const w = 480;
  const h = 680;
  const left = Math.max(0, (window.screen.width - w) / 2);
  const top = Math.max(0, (window.screen.height - h) / 2);
  return window.open("about:blank", name, `popup,width=${w},height=${h},left=${left},top=${top}`);
}

export async function http<T>(url: string, init: RequestInit & { token: string }): Promise<T> {
  const { token, ...rest } = init;
  const res = await fetch(url, {
    ...rest,
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...(rest.headers ?? {}) },
  });
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error((body as { error?: { message?: string } })?.error?.message || `HTTP ${res.status}`) as Error & { status: number };
    err.status = res.status;
    throw err;
  }
  return body as T;
}
