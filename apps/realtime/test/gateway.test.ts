import { SignJWT } from "jose";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Coalescer, fetchFriendIds, routeEvent, verifyAccess, type Emitter } from "../src/gateway.js";

const key = new TextEncoder().encode("test-only-jwt-signing-key-000000000000");
const cfg = { jwtKey: key, coreApiUrl: "http://core", serviceToken: "svc", coalesceMs: 10 };

async function token(claims: Record<string, unknown>, iss = "jingle-core") {
  return new SignJWT(claims).setProtectedHeader({ alg: "HS256" }).setIssuer(iss).setExpirationTime("5m").sign(key);
}

function fakeEmitter() {
  const sent: [string, string, unknown][] = [];
  const resynced: string[] = [];
  const e: Emitter = {
    toRoom: (room, event, payload) => sent.push([room, event, payload]),
    resyncUser: async (id) => {
      resynced.push(id);
    },
  };
  return { e, sent, resynced };
}

describe("handshake auth (NFR-SEC-05)", () => {
  it("accepts a core-api access token", async () => {
    expect(await verifyAccess(await token({ sub: "u1", typ: "access" }), cfg)).toBe("u1");
  });
  it("rejects refresh tokens, wrong issuers, garbage and missing tokens", async () => {
    await expect(verifyAccess(await token({ sub: "u1", typ: "refresh" }), cfg)).rejects.toThrow();
    await expect(verifyAccess(await token({ sub: "u1", typ: "access" }, "evil"), cfg)).rejects.toThrow();
    await expect(verifyAccess("not.a.jwt", cfg)).rejects.toThrow();
    await expect(verifyAccess(undefined, cfg)).rejects.toThrow();
  });
});

describe("event routing (ADR-0018: hints, never card payloads)", () => {
  afterEach(() => vi.useRealTimers());

  it("coalesces a burst of plays into one hint per friend room", () => {
    vi.useFakeTimers();
    const { e, sent } = fakeEmitter();
    const c = new Coalescer(2000);
    for (let i = 0; i < 5; i++) routeEvent("events:listen", { data: JSON.stringify({ user_id: "u1", raw: {} }) }, e, c);
    expect(sent).toEqual([]);
    vi.advanceTimersByTime(2000);
    expect(sent).toEqual([
      ["friends:u1", "feed:update", { user_id: "u1" }],
      ["user:u1", "me:update", {}],
    ]);
    // payload carries no track, route or time: privacy is applied by the REST fetch
    expect(JSON.stringify(sent)).not.toContain("raw");
  });

  it("friendship and block changes resync both users' rooms", () => {
    const { e, sent, resynced } = fakeEmitter();
    const out = routeEvent("events:domain", { type: "block.created", data: JSON.stringify({ user_ids: ["a", "b"] }) }, e, new Coalescer(1));
    expect(out).toBe("block.created:2");
    expect(resynced).toEqual(["a", "b"]);
    expect(sent.map((s) => s[0])).toEqual(["user:a", "user:b"]);
  });

  it("notify goes only to the recipient; unknown and malformed entries are ignored", () => {
    const { e, sent } = fakeEmitter();
    routeEvent("events:domain", { type: "notify", data: JSON.stringify({ user_id: "b", type: "friend_request", id: "r1" }) }, e, new Coalescer(1));
    expect(sent).toEqual([["user:b", "notify", { type: "friend_request", id: "r1" }]]);
    expect(routeEvent("events:domain", { type: "weird", data: "{}" }, e, new Coalescer(1))).toBe("ignored:weird");
    expect(routeEvent("events:listen", { data: "{bad" }, e, new Coalescer(1))).toBe("ignored:bad-json");
    expect(routeEvent("events:listen", { data: "{}" }, e, new Coalescer(1))).toBe("ignored:no-user");
  });
});

describe("friend lookup", () => {
  it("uses the service token and keeps only string ids", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify(["a", 3, "b"]), { status: 200 }));
    expect(await fetchFriendIds("u1", cfg, fetcher)).toEqual(["a", "b"]);
    expect(fetcher).toHaveBeenCalledWith("http://core/internal/users/u1/friends", { headers: { "X-Service-Token": "svc" } });
  });
  it("throws when core-api refuses", async () => {
    await expect(fetchFriendIds("u1", cfg, async () => new Response("", { status: 401 }))).rejects.toThrow();
  });
});
