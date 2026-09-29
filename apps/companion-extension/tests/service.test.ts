import { describe, expect, it, vi } from "vitest";
import { Companion } from "../src/background/service";
import { memoryKV, normaliseOrigin, STORAGE_KEYS } from "../src/shared/settings";
import type { TrackState } from "../src/shared/types";

const TOKEN = "jgl_abcdefghijklmnop";
const TOKEN_B = "jgl_bbbbbbbbbbbbbbbb";
const YTM = "https://music.youtube.com/watch?v=dQw4w9WgXcQ";

function setup(opts: { online?: boolean } = {}) {
  let now = Date.UTC(2026, 8, 29, 10, 0, 0);
  let online = opts.online ?? true;
  let submitStatus = 200;
  let submitAttempts = 0;
  const calls: { url: string; init?: RequestInit }[] = [];
  const fetchImpl = vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith("/submit-listens")) submitAttempts++;
    if (!online) throw new TypeError("Failed to fetch");
    if (url.endsWith("/ingest/1/validate-token")) {
      const auth = (init?.headers as Record<string, string>).Authorization;
      const user = auth === `Token ${TOKEN}` ? "aanya" : auth === `Token ${TOKEN_B}` ? "bela" : null;
      return new Response(JSON.stringify({ code: 200, message: "ok", valid: user !== null, ...(user ? { user_name: user } : {}) }), { status: 200 });
    }
    if (submitStatus !== 200) return new Response("{}", { status: submitStatus });
    calls.push({ url, ...(init ? { init } : {}) }); // delivered submissions only
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
    setSubmitStatus: (s: number) => (submitStatus = s),
    attempts: () => submitAttempts,
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
    expect(await c.pair(TOKEN, "http://127.0.0.1:8080")).toEqual({ ok: true, userName: "aanya" });
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
    const sub = calls.find((x) => x.url === "http://127.0.0.1:8080/ingest/1/submit-listens");
    expect(sub?.init?.method).toBe("POST");
    expect((sub?.init?.headers as Record<string, string>).Authorization).toBe(`Token ${TOKEN}`);
    expect(JSON.parse(String(sub?.init?.body))).toMatchObject({ listen_type: "playing_now" });
    expect(calls.every((x) => x.url.startsWith("http://127.0.0.1:8080/"))).toBe(true);
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

  /** 5 s ticks with a content keepalive every 15 s, like the real observer. */
  async function playFor(h: ReturnType<typeof setup>, seconds: number, state: TrackState = t()) {
    for (let s = 5; s <= seconds; s += 5) {
      h.advance(5000);
      if (s % 15 === 0) await h.c.onTrack(1, YTM, { ...state, positionMs: undefined });
      await h.c.onTick();
    }
  }

  it("queues the single while offline and delivers it when back", async () => {
    const h = setup();
    await h.c.pair(TOKEN, null);
    await h.c.onTrack(1, YTM, t());
    h.setOnline(false);
    await playFor(h, 120);
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

  it("M1: pairing a new token drops the previous account's queue and in-progress play", async () => {
    const h = setup();
    await h.c.pair(TOKEN, null); // account A
    await h.c.onTrack(1, YTM, t());
    h.setOnline(false);
    await playFor(h, 120);
    expect((await h.c.status()).queueSize).toBe(1);
    h.setOnline(true);
    const before = h.submissions().length;
    expect((await h.c.pair(TOKEN_B, null)).ok).toBe(true); // account B on the same browser
    expect((await h.c.status()).queueSize).toBe(0);
    expect((await h.c.status()).nowPlaying).toBeNull();
    h.advance(3_600_000);
    await h.c.onTick();
    expect(h.submissions().length).toBe(before); // nothing of A's sent with B's token
  });

  it("a rejected token (401) suspends all sending, including queue retries, until re-paired", async () => {
    const h = setup();
    await h.c.pair(TOKEN, null);
    h.setSubmitStatus(401);
    await h.c.onTrack(1, YTM, t());
    expect((await h.c.status()).lastError).toBe("token_rejected");
    const attempts = h.attempts();
    await playFor(h, 300);
    h.advance(3_600_000);
    await h.c.onTick();
    expect(h.attempts()).toBe(attempts);
    h.setSubmitStatus(200);
    await h.c.pair(TOKEN, null);
    expect((await h.c.status()).lastError).toBeNull();
    await h.c.onTrack(1, YTM, t({ title: "Another" }));
    expect(h.attempts()).toBe(attempts + 1);
  });

  it("switching a platform off stops its play immediately", async () => {
    const h = setup();
    await h.c.pair(TOKEN, null);
    await h.c.onTrack(1, YTM, t());
    const n = h.submissions().length;
    await h.c.updateSettings({ platforms: { YOUTUBE_MUSIC: false, SPOTIFY: true, APPLE_MUSIC: true, AMAZON_MUSIC: true } });
    h.advance(30_000);
    await h.c.onTick();
    expect(h.submissions().length).toBe(n);
  });

  it("rejects malformed track messages at the worker", async () => {
    const h = setup();
    await h.c.pair(TOKEN, null);
    await h.c.onTrack(1, YTM, { platform: "YOUTUBE_MUSIC", artist: 5, title: "x", isPlaying: true });
    await h.c.onTrack(1, YTM, { platform: "NAPSTER", artist: "a", title: "x", isPlaying: true });
    expect(h.submissions()).toEqual([]);
    await h.c.onTrack(1, YTM, { ...t(), artist: "a".repeat(9000), originUrl: "javascript:alert(1)" });
    const body = JSON.parse(String(h.calls.at(-1)?.init?.body)) as { payload: { track_metadata: { artist_name: string; additional_info: Record<string, unknown> } }[] };
    expect(body.payload[0]!.track_metadata.artist_name).toHaveLength(512);
    expect(body.payload[0]!.track_metadata.additional_info.origin_url).toBeUndefined();
  });

  it("defaults to the ADR-0016 origin", async () => {
    const { c } = setup();
    expect((await c.settings()).origin).toBe("http://127.0.0.1:8080");
  });

  it("changing the origin signs out", async () => {
    const { c, local } = setup();
    await c.pair(TOKEN, null);
    await c.updateSettings({ origin: "https://jingle.example.org/" });
    expect(await local.get(STORAGE_KEYS.auth)).toBeUndefined();
    expect((await c.settings()).origin).toBe("https://jingle.example.org");
  });

  it("origin validation", () => {
    expect(normaliseOrigin("http://127.0.0.1:8080/")).toBe("http://127.0.0.1:8080");
    expect(normaliseOrigin("http://localhost:8080")).toBe("http://localhost:8080");
    expect(normaliseOrigin("http://localhost:3000")).toBeNull(); // cannot be granted
    expect(normaliseOrigin("https://jingle.example.org:8443/x?y")).toBe("https://jingle.example.org:8443");
    expect(normaliseOrigin("http://jingle.example.org")).toBeNull();
    expect(normaliseOrigin("https://user:pw@jingle.example.org")).toBeNull();
    expect(normaliseOrigin("javascript:alert(1)")).toBeNull();
  });
});
