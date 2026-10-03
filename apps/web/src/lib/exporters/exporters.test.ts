import { afterEach, describe, expect, it, vi } from "vitest";
import { appleIdFromLink, score, MATCH_THRESHOLD, type ExportSong } from "./common";

vi.mock("@/lib/api", () => ({ api: vi.fn() }));
import { api } from "@/lib/api";
import { exportToSpotify } from "./spotify";
import { exportToYouTube } from "./youtube";
import { exportToApple } from "./apple";

const songs: ExportSong[] = [
  { key: "prateek kuhad|kasoor", title: "Kasoor", artist: "Prateek Kuhad", appleId: "111" },
  { key: "anuv jain|husn", title: "Husn", artist: "Anuv Jain", appleId: null },
  { key: "nobody|unreleased", title: "Unreleased", artist: "Nobody", appleId: null },
];

type Call = { url: string; method: string; body: unknown };
function mockFetch(route: (c: Call) => unknown) {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: RequestInit = {}) => {
      const c = { url: String(url), method: init.method ?? "GET", body: init.body ? JSON.parse(String(init.body)) : undefined };
      calls.push(c);
      const r = route(c);
      if (r instanceof Response) return r;
      return new Response(r === undefined ? null : JSON.stringify(r), { status: r === undefined ? 204 : 200 });
    }),
  );
  return calls;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.mocked(api).mockReset();
});

describe("matching", () => {
  it("prefers the original by the right artist", () => {
    expect(score("Kasoor", "Prateek Kuhad", "Kasoor", "Prateek Kuhad")).toBeGreaterThan(MATCH_THRESHOLD);
    expect(score("Kasoor", "Prateek Kuhad", "Kasoor", "Piano Tribute Players")).toBe(0);
    expect(score("Kasoor", "Prateek Kuhad", "Kasoor (Lofi Remix)", "Prateek Kuhad")).toBeLessThan(score("Kasoor", "Prateek Kuhad", "Kasoor", "Prateek Kuhad"));
  });
  it("reads exact Apple ids from Jingle links", () => {
    expect(appleIdFromLink("https://music.apple.com/song/1440818") ).toBe("1440818");
    expect(appleIdFromLink("https://music.apple.com/in/song/kasoor/1440818")).toBe("1440818");
    expect(appleIdFromLink(null)).toBeNull();
  });
});

describe("Spotify", () => {
  const route = (c: Call) => {
    if (c.url.includes("/search?")) {
      const q = decodeURIComponent(new URL(c.url).searchParams.get("q") ?? "");
      if (q.includes("Kasoor")) return { tracks: { items: [{ uri: "spotify:track:K", name: "Kasoor", artists: [{ name: "Prateek Kuhad" }] }] } };
      if (q.includes("Husn")) return { tracks: { items: [{ uri: "spotify:track:H", name: "Husn", artists: [{ name: "Anuv Jain" }] }] } };
      return { tracks: { items: [] } };
    }
    if (c.url.endsWith("/me")) return { id: "me" };
    if (c.url.endsWith("/users/me/playlists")) return { id: "PL1", external_urls: { spotify: "https://open.spotify.com/playlist/PL1" } };
    return undefined;
  };

  it("creates a private playlist in exact order and reports what's missing", async () => {
    const calls = mockFetch(route);
    const r = await exportToSpotify("tok", "Crew", songs, null, () => {});
    expect(r.url).toBe("https://open.spotify.com/playlist/PL1");
    expect(r.placedKeys).toEqual([songs[0]!.key, songs[1]!.key]);
    expect(r.missing.map((s) => s.title)).toEqual(["Unreleased"]);
    const create = calls.find((c) => c.url.endsWith("/users/me/playlists"))!;
    expect(create.body).toMatchObject({ name: "Crew · Jingle", public: false });
    expect(calls.find((c) => c.method === "PUT")!.body).toEqual({ uris: ["spotify:track:K", "spotify:track:H"] });
  });

  it("updates last time's copy instead of making a duplicate", async () => {
    const calls = mockFetch(route);
    const r = await exportToSpotify("tok", "Crew", songs, { external_id: "OLD", url: "https://open.spotify.com/playlist/OLD", track_keys: [] }, () => {});
    expect(r.externalId).toBe("OLD");
    expect(calls.some((c) => c.url.endsWith("/playlists") && c.method === "POST")).toBe(false);
    expect(calls.find((c) => c.method === "PUT")!.url).toContain("/playlists/OLD/tracks");
  });
});

describe("YouTube Music", () => {
  it("appends only what's new when the copy is still in order", async () => {
    vi.mocked(api).mockResolvedValue({ matches: { [songs[0]!.key]: "AAAAAAAAAAA", [songs[1]!.key]: "BBBBBBBBBBB", [songs[2]!.key]: null } });
    const calls = mockFetch((c) => {
      if (c.url.includes("/playlistItems?part=snippet&playlistId")) return { items: [{ id: "i1", snippet: { resourceId: { videoId: "AAAAAAAAAAA" } } }] };
      return { id: "x" };
    });
    const r = await exportToYouTube("tok", "c1", "Crew", songs, { external_id: "YT1", url: "https://music.youtube.com/playlist?list=YT1", track_keys: [] }, () => {});
    const inserts = calls.filter((c) => c.method === "POST" && c.url.includes("/playlistItems"));
    expect(inserts.map((c) => (c.body as { snippet: { resourceId: { videoId: string } } }).snippet.resourceId.videoId)).toEqual(["BBBBBBBBBBB"]);
    expect(calls.some((c) => c.method === "DELETE")).toBe(false);
    expect(r.url).toBe("https://music.youtube.com/playlist?list=YT1");
    expect(r.missing.map((s) => s.title)).toEqual(["Unreleased"]);
  });

  it("creates a new private playlist and adds songs in order", async () => {
    vi.mocked(api).mockResolvedValue({ matches: { [songs[0]!.key]: "AAAAAAAAAAA", [songs[1]!.key]: "BBBBBBBBBBB" } });
    const calls = mockFetch((c) => (c.url.includes("/playlists?part=snippet,status") ? { id: "NEW" } : { id: "x" }));
    const r = await exportToYouTube("tok", "c1", "Crew", songs.slice(0, 2), null, () => {});
    expect(calls[0]!.body).toMatchObject({ status: { privacyStatus: "private" } });
    const order = calls.filter((c) => c.url.includes("/playlistItems")).map((c) => (c.body as { snippet: { resourceId: { videoId: string } } }).snippet.resourceId.videoId);
    expect(order).toEqual(["AAAAAAAAAAA", "BBBBBBBBBBB"]);
    expect(r.externalId).toBe("NEW");
  });
});

describe("Apple Music", () => {
  function fakeMusic() {
    const calls: { path: string; method: string; body?: unknown }[] = [];
    return {
      calls,
      storefrontId: "in",
      authorize: async () => "user-token",
      api: {
        music: async (path: string, query?: Record<string, unknown>, opts?: { fetchOptions?: RequestInit }) => {
          calls.push({ path, method: opts?.fetchOptions?.method ?? "GET", body: opts?.fetchOptions?.body ? JSON.parse(String(opts.fetchOptions.body)) : undefined });
          if (path.includes("/search")) {
            const term = String(query?.term ?? "");
            return { data: { results: { songs: { data: term.includes("Husn") ? [{ id: "222", attributes: { name: "Husn", artistName: "Anuv Jain" } }] : [] } } } };
          }
          if (path === "v1/me/library/playlists") return { data: { data: [{ id: "p.NEW" }] } };
          return { data: {} };
        },
      },
    };
  }

  it("uses exact ids, searches the rest, creates in order", async () => {
    const m = fakeMusic();
    const r = await exportToApple(m, "Crew", songs, null, () => {});
    const create = m.calls.find((c) => c.path === "v1/me/library/playlists")!;
    expect((create.body as { relationships: { tracks: { data: { id: string }[] } } }).relationships.tracks.data.map((d) => d.id)).toEqual(["111", "222"]);
    expect(m.calls.filter((c) => c.path.includes("/search"))).toHaveLength(2); // Kasoor had its exact id
    expect(r.url).toBe("https://music.apple.com/library/playlist/p.NEW");
    expect(r.missing.map((s) => s.title)).toEqual(["Unreleased"]);
  });

  it("appends only new songs and reports removed ones (Apple can't remove)", async () => {
    const m = fakeMusic();
    const prior = { external_id: "p.OLD", url: "https://music.apple.com/library/playlist/p.OLD", track_keys: [songs[0]!.key, "gone|song"] };
    const r = await exportToApple(m, "Crew", songs.slice(0, 2), prior, () => {});
    const append = m.calls.find((c) => c.path === "v1/me/library/playlists/p.OLD/tracks")!;
    expect((append.body as { data: { id: string }[] }).data.map((d) => d.id)).toEqual(["222"]);
    expect(r.stale).toBe(1);
    expect(r.placedKeys).toEqual([songs[0]!.key, songs[1]!.key]);
  });
});
