import { describe, expect, it, vi } from "vitest";
import { Companion } from "../src/background/service";
import { memoryKV, normaliseOrigin, STORAGE_KEYS } from "../src/shared/settings";
import type { TrackState } from "../src/shared/types";

const TOKEN = "jgl_abcdefghijklmnop";
const YTM = "https://music.youtube.com/watch?v=dQw4w9WgXcQ";

function setup(opts: { online?: boolean } = {}) {
  let now = Date.UTC(2026, 8, 29, 10, 0, 0);
  let online = opts.online ?? true;
  const calls: { url: string; init?: RequestInit }[] = [];
  const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
    if (!online) throw new TypeError("Failed to fetch");
    calls.push({ url, ...(init ? { init } : {}) }); // delivered requests only
    if (url.endsWith("/ingest/1/validate-token")) {
      const auth = (init?.headers as Record<string, string>).Authorization;
      const valid = auth === `Token ${TOKEN}`;
      return new Response(JSON.stringify({ code: 200, message: "Token valid.", valid, ...(valid ? { user_name: "aanya" } : {}) }), { status: 200 });
    }
    return new Response(JSON.stringify({ status: "ok" }), { status: 200 });
  });
  const local = memoryKV();
  const c = new Companion({ local, session: memoryKV(), fetch: fetchImpl, now: () => now });
  return {
    c,
    local,
    calls,
    advance: (ms: number) => (now += ms),
    setOnline: (v: boolean) => (online = v),
    submissions: () => calls.filter((x) => x.url.endsWith("/submit-listens")).map((x) => JSON.parse(String(x.init?.body)) as { listen_type: string }),
  };
}

const t = (over: Partial<TrackState> = {}): TrackState => ({
  platform: "YOUTUBE_MUSIC",
  artist: "Artist",
  title: "Song",
  durationMs: 200_000,
  positionMs: 0,
  isPlaying: true,
  ...over,
});

describe("Companion service worker core", () => {
  it("pairs only from the configured origin", async () => {
    const { c, local } = setup();
    expect(await c.pair(TOKEN, "https://evil.example")).toEqual({ ok: false, error: "wrong_origin" });
    expect(await local.get(STORAGE_KEYS.auth)).toBeUndefined();
    expect(await c.pair(TOKEN, "http://localhost:8080")).toEqual({ ok: true, userName: "aanya" });
    expect(await local.get(STORAGE_KEYS.auth)).toEqual({ token: TOKEN, userName: "aanya" });
  });

  it("rejects a token the server says is invalid", async () => {
    const { c } = setup();
    expect(await c.pair("jgl_wrongwrongwrong", null)).toEqual({ ok: false, error: "invalid_token" });
  });

  it("sends nothing before pairing", async () => {
    const { c, submissions } = setup();
    await c.onTrack(1, YTM, t());
    expect(submissions()).toEqual([]);
  });

  it("sends playing_now with the token to {origin}/ingest/1/submit-listens", async () => {
    const { c, calls } = setup();
    await c.pair(TOKEN, null);
    await c.onTrack(1, YTM, t());
    const sub = calls.find((x) => x.url === "http://localhost:8080/ingest/1/submit-listens");
    expect(sub?.init?.method).toBe("POST");
    expect((sub?.init?.headers as Record<string, string>).Authorization).toBe(`Token ${TOKEN}`);
    expect(JSON.parse(String(sub?.init?.body))).toMatchObject({ listen_type: "playing_now" });
    expect(calls.every((x) => x.url.startsWith("http://localhost:8080/"))).toBe(true);
  });

  it("ignores a state whose platform does not match the sending tab's host", async () => {
    const { c, submissions } = setup();
    await c.pair(TOKEN, null);
    await c.onTrack(1, "https://evil.example/", t());
    await c.onTrack(2, "https://open.spotify.com/", t()); // claims YOUTUBE_MUSIC
    expect(submissions()).toEqual([]);
  });

  it("respects pause-sharing and per-platform toggles", async () => {
    const { c, submissions } = setup();
    await c.pair(TOKEN, null);
    await c.updateSettings({ platforms: { YOUTUBE_MUSIC: false, SPOTIFY: true, APPLE_MUSIC: true, AMAZON_MUSIC: true } });
    await c.onTrack(1, YTM, t());
    await c.updateSettings({ paused: true, platforms: { YOUTUBE_MUSIC: true, SPOTIFY: true, APPLE_MUSIC: true, AMAZON_MUSIC: true } });
    await c.onTrack(1, YTM, t());
    expect(submissions()).toEqual([]);
  });

  it("queues the single while offline and delivers it when back", async () => {
    const h = setup();
    await h.c.pair(TOKEN, null);
    await h.c.onTrack(1, YTM, t());
    h.setOnline(false);
    for (let i = 0; i < 24; i++) {
      h.advance(5000);
      await h.c.onTick();
    }
    expect((await h.c.status()).queueSize).toBe(1);
    expect((await h.c.status()).lastError).toBe("offline");
    h.setOnline(true);
    h.advance(120_000);
    await h.c.onTick();
    const st = await h.c.status();
    expect(st.queueSize).toBe(0);
    expect(st.lastError).toBeNull();
    expect(h.submissions().filter((s) => s.listen_type === "single")).toHaveLength(1);
  });

  it("changing the origin signs out", async () => {
    const { c, local } = setup();
    await c.pair(TOKEN, null);
    await c.updateSettings({ origin: "https://jingle.example.org/" });
    expect(await local.get(STORAGE_KEYS.auth)).toBeUndefined();
    expect((await c.settings()).origin).toBe("https://jingle.example.org");
  });

  it("origin validation", () => {
    expect(normaliseOrigin("http://localhost:8080/")).toBe("http://localhost:8080");
    expect(normaliseOrigin("http://jingle.example.org")).toBeNull();
    expect(normaliseOrigin("https://user:pw@jingle.example.org")).toBeNull();
    expect(normaliseOrigin("javascript:alert(1)")).toBeNull();
  });
});
