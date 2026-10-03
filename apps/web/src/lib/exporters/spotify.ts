import { MATCH_THRESHOLD, http, openPopup, playlistDescription, playlistName, score, type ExportResult, type ExportSong, type PriorExport, type Progress } from "./common";

/**
 * Spotify (official Web API, Authorization Code + PKCE: no client secret, the token stays in this
 * page). Creates a private playlist in the listener's account, or replaces the songs of the copy
 * made last time, in exact order. Search results are used only to build that playlist (D-BR-01).
 */
const API = "https://api.spotify.com/v1";
const SCOPES = "playlist-modify-private playlist-modify-public";
export const SPOTIFY_CALLBACK_PATH = "/connect/spotify/callback";

function b64url(bytes: ArrayBuffer | Uint8Array): string {
  const b = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  return btoa(String.fromCharCode(...b)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/** Popup login; resolves with an access token (memory only). */
export async function spotifyLogin(clientId: string, popup: Window | null): Promise<string> {
  const verifier = b64url(crypto.getRandomValues(new Uint8Array(48)));
  const challenge = b64url(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)));
  const state = b64url(crypto.getRandomValues(new Uint8Array(16)));
  const redirect = `${window.location.origin}${SPOTIFY_CALLBACK_PATH}`;
  const url = new URL("https://accounts.spotify.com/authorize");
  url.search = new URLSearchParams({
    response_type: "code",
    client_id: clientId,
    scope: SCOPES,
    redirect_uri: redirect,
    code_challenge_method: "S256",
    code_challenge: challenge,
    state,
  }).toString();
  const win = popup ?? openPopup("jingle-spotify");
  if (!win) throw new Error("Allow pop-ups for Jingle to log in to Spotify.");
  win.location.href = url.toString();

  const code = await new Promise<string>((resolve, reject) => {
    const done = (e: MessageEvent) => {
      if (e.origin !== window.location.origin || e.data?.type !== "jingle:spotify") return;
      window.removeEventListener("message", done);
      clearInterval(closed);
      if (e.data.state !== state) reject(new Error("Spotify login didn't match. Try again."));
      else if (e.data.error) reject(new Error(e.data.error === "access_denied" ? "Spotify login was cancelled." : "Spotify login failed."));
      else resolve(e.data.code as string);
    };
    window.addEventListener("message", done);
    const closed = window.setInterval(() => {
      if (win.closed) {
        window.removeEventListener("message", done);
        clearInterval(closed);
        reject(new Error("Spotify login was closed."));
      }
    }, 500);
  });

  const res = await fetch("https://accounts.spotify.com/api/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ grant_type: "authorization_code", code, redirect_uri: redirect, client_id: clientId, code_verifier: verifier }),
  });
  if (!res.ok) throw new Error("Spotify login failed.");
  return ((await res.json()) as { access_token: string }).access_token;
}

interface SpotifyTrack {
  uri: string;
  name: string;
  artists: { name: string }[];
}

export async function findOnSpotify(token: string, s: ExportSong): Promise<string | null> {
  const q = `track:${s.title.replace(/"/g, "")} artist:${s.artist.replace(/"/g, "")}`;
  const r = await http<{ tracks: { items: SpotifyTrack[] } }>(`${API}/search?${new URLSearchParams({ q, type: "track", limit: "5" })}`, { token });
  let best: { uri: string; sc: number } | null = null;
  for (const t of r.tracks?.items ?? []) {
    const sc = score(s.title, s.artist, t.name, t.artists.map((a) => a.name).join(" "));
    if (sc >= MATCH_THRESHOLD && (!best || sc > best.sc)) best = { uri: t.uri, sc };
  }
  return best?.uri ?? null;
}

export async function exportToSpotify(
  token: string,
  circle: string,
  songs: ExportSong[],
  prior: PriorExport | null,
  progress: Progress,
): Promise<ExportResult> {
  const uris: string[] = [];
  const placed: string[] = [];
  const missing: ExportSong[] = [];
  for (const [i, s] of songs.entries()) {
    progress(`Finding songs on Spotify (${i + 1} of ${songs.length})`);
    const uri = await findOnSpotify(token, s);
    if (uri) {
      uris.push(uri);
      placed.push(s.key);
    } else missing.push(s);
  }

  // Update the copy made last time if it still exists; otherwise create a new private playlist.
  let id = prior?.external_id ?? null;
  let url = prior?.url ?? null;
  if (id) {
    try {
      await http(`${API}/playlists/${id}/tracks`, { token, method: "PUT", body: JSON.stringify({ uris: uris.slice(0, 100) }) });
    } catch (e) {
      if ((e as { status?: number }).status === 404 || (e as { status?: number }).status === 403) id = null;
      else throw e;
    }
  }
  if (!id) {
    progress("Creating your playlist");
    const me = await http<{ id: string }>(`${API}/me`, { token });
    const pl = await http<{ id: string; external_urls: { spotify: string } }>(`${API}/users/${encodeURIComponent(me.id)}/playlists`, {
      token,
      method: "POST",
      body: JSON.stringify({ name: playlistName(circle), description: playlistDescription(circle), public: false }),
    });
    id = pl.id;
    url = pl.external_urls.spotify;
    if (uris.length) await http(`${API}/playlists/${id}/tracks`, { token, method: "PUT", body: JSON.stringify({ uris: uris.slice(0, 100) }) });
  }
  for (let i = 100; i < uris.length; i += 100) {
    await http(`${API}/playlists/${id}/tracks`, { token, method: "POST", body: JSON.stringify({ uris: uris.slice(i, i + 100) }) });
  }
  return { externalId: id!, url: url ?? `https://open.spotify.com/playlist/${id}`, placedKeys: placed, missing };
}
