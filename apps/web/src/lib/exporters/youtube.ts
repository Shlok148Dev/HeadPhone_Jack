import { api } from "@/lib/api";
import { http, playlistDescription, playlistName, type ExportResult, type ExportSong, type PriorExport, type Progress } from "./common";

/**
 * YouTube Music (official YouTube Data API v3). Jingle's server finds each song's video (cached per
 * song, preferring YouTube's official "Topic" audio); the listener's browser, logged in with Google
 * (scope: youtube), creates a private playlist in their account that YouTube Music shows too.
 * Updating keeps what's already in order and appends the rest; otherwise it rebuilds the list.
 */
const API = "https://www.googleapis.com/youtube/v3";
const SCOPE = "https://www.googleapis.com/auth/youtube";

type Gis = {
  accounts: {
    oauth2: {
      initTokenClient: (cfg: { client_id: string; scope: string; callback: (r: { access_token?: string; error?: string }) => void; error_callback?: (e: { type: string }) => void }) => {
        requestAccessToken: (o?: { prompt?: string }) => void;
      };
    };
  };
};

function loadGis(): Promise<Gis> {
  const w = window as unknown as { google?: Gis };
  if (w.google?.accounts?.oauth2) return Promise.resolve(w.google);
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = "https://accounts.google.com/gsi/client";
    s.async = true;
    s.onload = () => (w.google?.accounts?.oauth2 ? resolve(w.google) : reject(new Error("Google login didn't load.")));
    s.onerror = () => reject(new Error("Google login didn't load."));
    document.head.appendChild(s);
  });
}

/** Must be called from a click (Google opens its own popup). Token stays in this page. */
export async function youtubeLogin(clientId: string): Promise<string> {
  const g = await loadGis();
  return new Promise((resolve, reject) => {
    const tc = g.accounts.oauth2.initTokenClient({
      client_id: clientId,
      scope: SCOPE,
      callback: (r) => (r.access_token ? resolve(r.access_token) : reject(new Error("Google login failed."))),
      error_callback: (e) => reject(new Error(e.type === "popup_closed" ? "Google login was closed." : "Google login failed.")),
    });
    tc.requestAccessToken({ prompt: "" });
  });
}

interface Item {
  id: string;
  snippet: { resourceId: { videoId: string } };
}

async function listItems(token: string, playlistId: string): Promise<Item[]> {
  const out: Item[] = [];
  let page: string | undefined;
  do {
    const q = new URLSearchParams({ part: "snippet", playlistId, maxResults: "50", ...(page ? { pageToken: page } : {}) });
    const r = await http<{ items: Item[]; nextPageToken?: string }>(`${API}/playlistItems?${q}`, { token });
    out.push(...r.items);
    page = r.nextPageToken;
  } while (page);
  return out;
}

async function addItem(token: string, playlistId: string, videoId: string) {
  await http(`${API}/playlistItems?part=snippet`, {
    token,
    method: "POST",
    body: JSON.stringify({ snippet: { playlistId, resourceId: { kind: "youtube#video", videoId } } }),
  });
}

export async function exportToYouTube(
  token: string,
  circleId: string,
  circle: string,
  songs: ExportSong[],
  prior: PriorExport | null,
  progress: Progress,
): Promise<ExportResult> {
  progress("Finding songs on YouTube Music");
  const { matches } = await api<{ matches: Record<string, string | null> }>(`/circles/${circleId}/playlist/youtube-matches`, { method: "POST" });
  const want = songs.filter((s) => matches[s.key]).map((s) => ({ s, vid: matches[s.key]! }));
  const missing = songs.filter((s) => !matches[s.key]);

  let id = prior?.external_id ?? null;
  if (id) {
    try {
      const existing = await listItems(token, id);
      const wantIds = want.map((w) => w.vid);
      // Remove what's no longer in the circle, then keep the copy only if it's still in order.
      for (const it of existing.filter((e) => !wantIds.includes(e.snippet.resourceId.videoId))) {
        await http(`${API}/playlistItems?id=${encodeURIComponent(it.id)}`, { token, method: "DELETE" });
      }
      const kept = existing.map((e) => e.snippet.resourceId.videoId).filter((v) => wantIds.includes(v));
      const inOrder = kept.every((v, i) => v === wantIds[i]);
      if (!inOrder) {
        for (const it of existing.filter((e) => wantIds.includes(e.snippet.resourceId.videoId))) {
          await http(`${API}/playlistItems?id=${encodeURIComponent(it.id)}`, { token, method: "DELETE" });
        }
      }
      const start = inOrder ? kept.length : 0;
      for (const [i, w] of want.slice(start).entries()) {
        progress(`Adding songs (${start + i + 1} of ${want.length})`);
        await addItem(token, id, w.vid);
      }
    } catch (e) {
      if ((e as { status?: number }).status === 404) id = null;
      else throw e;
    }
  }
  if (!id) {
    progress("Creating your playlist");
    const pl = await http<{ id: string }>(`${API}/playlists?part=snippet,status`, {
      token,
      method: "POST",
      body: JSON.stringify({ snippet: { title: playlistName(circle), description: playlistDescription(circle) }, status: { privacyStatus: "private" } }),
    });
    id = pl.id;
    for (const [i, w] of want.entries()) {
      progress(`Adding songs (${i + 1} of ${want.length})`);
      await addItem(token, id, w.vid);
    }
  }
  return { externalId: id, url: `https://music.youtube.com/playlist?list=${id}`, placedKeys: want.map((w) => w.s.key), missing };
}
