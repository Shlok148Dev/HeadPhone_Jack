import { api } from "@/lib/api";
import { MATCH_THRESHOLD, playlistDescription, playlistName, score, type ExportResult, type ExportSong, type PriorExport, type Progress } from "./common";

/**
 * Apple Music (official MusicKit JS v3). Jingle's server signs the developer token; the listener
 * authorises in Apple's own window and their Music User Token stays inside MusicKit in this page.
 * Most songs already carry their exact Apple catalogue id (from Jingle's Apple matching); the rest
 * are searched in the listener's storefront. Apple's API can create a library playlist and append
 * to it, but not remove or reorder: an update appends new songs and reports removed ones honestly.
 */
const MUSICKIT = "https://js-cdn.music.apple.com/musickit/v3/musickit.js";

interface MusicKitInstance {
  authorize: () => Promise<string>;
  storefrontId?: string;
  api: { music: (path: string, query?: Record<string, unknown>, opts?: { fetchOptions?: RequestInit }) => Promise<{ data: unknown }> };
}
type MusicKitGlobal = {
  configure: (cfg: { developerToken: string; app: { name: string; build: string } }) => Promise<MusicKitInstance>;
  getInstance: () => MusicKitInstance;
};

function loadMusicKit(): Promise<MusicKitGlobal> {
  const w = window as unknown as { MusicKit?: MusicKitGlobal };
  if (w.MusicKit) return Promise.resolve(w.MusicKit);
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = MUSICKIT;
    s.async = true;
    s.setAttribute("data-web-components", "");
    document.addEventListener("musickitloaded", () => (w.MusicKit ? resolve(w.MusicKit) : reject(new Error("Apple Music didn't load."))), { once: true });
    s.onerror = () => reject(new Error("Apple Music didn't load."));
    document.head.appendChild(s);
  });
}

/** Load, configure and authorise (Apple opens its own window). Returns the configured instance. */
export async function appleLogin(): Promise<MusicKitInstance> {
  const [{ token }, MK] = await Promise.all([api<{ token: string }>("/exports/apple/token"), loadMusicKit()]);
  const music = await MK.configure({ developerToken: token, app: { name: "Jingle", build: "1" } });
  await music.authorize();
  return music;
}

async function findOnApple(music: MusicKitInstance, s: ExportSong): Promise<string | null> {
  if (s.appleId) return s.appleId;
  const sf = music.storefrontId || "in";
  const r = (await music.api.music(`v1/catalog/${sf}/search`, { term: `${s.artist} ${s.title}`, types: "songs", limit: 5 })) as {
    data: { results?: { songs?: { data: { id: string; attributes: { name: string; artistName: string } }[] } } };
  };
  let best: { id: string; sc: number } | null = null;
  for (const it of r.data.results?.songs?.data ?? []) {
    const sc = score(s.title, s.artist, it.attributes.name, it.attributes.artistName);
    if (sc >= MATCH_THRESHOLD && (!best || sc > best.sc)) best = { id: it.id, sc };
  }
  return best?.id ?? null;
}

export async function exportToApple(
  music: MusicKitInstance,
  circle: string,
  songs: ExportSong[],
  prior: PriorExport | null,
  progress: Progress,
): Promise<ExportResult> {
  const placedBefore = new Set(prior?.track_keys ?? []);
  const ids: { key: string; id: string }[] = [];
  const missing: ExportSong[] = [];
  for (const [i, s] of songs.entries()) {
    progress(`Finding songs on Apple Music (${i + 1} of ${songs.length})`);
    const id = await findOnApple(music, s);
    if (id) ids.push({ key: s.key, id });
    else missing.push(s);
  }
  const body = (list: { id: string }[]) => JSON.stringify({ data: list.map((x) => ({ id: x.id, type: "songs" })) });

  if (prior?.external_id) {
    // Append only what's new, at the end (Apple can't remove or reorder via its API).
    const fresh = ids.filter((x) => !placedBefore.has(x.key));
    try {
      if (fresh.length) {
        progress("Adding new songs to your playlist");
        await music.api.music(`v1/me/library/playlists/${prior.external_id}/tracks`, undefined, { fetchOptions: { method: "POST", body: body(fresh) } });
      }
      const stale = [...placedBefore].filter((k) => !songs.some((s) => s.key === k)).length;
      return { externalId: prior.external_id, url: prior.url, placedKeys: [...placedBefore].filter((k) => songs.some((s) => s.key === k)).concat(fresh.map((x) => x.key)), missing, stale };
    } catch {
      /* the copy was deleted in Apple Music: make a new one below */
    }
  }
  progress("Creating your playlist");
  const r = (await music.api.music("v1/me/library/playlists", undefined, {
    fetchOptions: {
      method: "POST",
      body: JSON.stringify({
        attributes: { name: playlistName(circle), description: playlistDescription(circle) },
        relationships: { tracks: { data: ids.map((x) => ({ id: x.id, type: "songs" })) } },
      }),
    },
  })) as { data: { data: { id: string }[] } };
  const id = r.data.data[0]!.id;
  return { externalId: id, url: `https://music.apple.com/library/playlist/${id}`, placedKeys: ids.map((x) => x.key), missing };
}

/** Connect (D-CONNECT-01): Apple's own sign-in; returns the Music User Token for Jingle to keep. */
export async function appleMusicUserToken(): Promise<string> {
  const [{ token }, MK] = await Promise.all([api<{ token: string }>("/exports/apple/token"), loadMusicKit()]);
  const music = await MK.configure({ developerToken: token, app: { name: "Jingle", build: "1" } });
  return music.authorize();
}
